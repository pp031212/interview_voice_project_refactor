from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFACTOR_ROOT = Path(__file__).resolve().parents[1]
if str(REFACTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(REFACTOR_ROOT))

from core.rubric import evaluate_answer_rubric, evaluate_overall_rubric  # noqa: E402


DEFAULT_SAMPLE_PATH = REFACTOR_ROOT / "data" / "rubric_calibration_samples.example.json"

DIMENSION_LABELS: dict[str, str] = {
    "relevance": "相关性",
    "technical_accuracy": "技术准确性",
    "completeness": "完整度",
    "depth_evidence": "深度与证据",
    "structure": "表达结构",
    "professional_credibility": "职业可信度",
}


@dataclass(frozen=True)
class SampleEvaluation:
    """Rubric evaluation result for one calibration sample."""

    sample_id: str
    rubric_score: float
    expected_score: float | None
    delta: float | None
    dimension_deltas: dict[str, float]
    rubric: dict[str, Any]


@dataclass(frozen=True)
class CalibrationReport:
    """Aggregated calibration report."""

    sample_count: int
    scored_sample_count: int
    mae: float | None
    bias: float | None
    dimension_bias: dict[str, float]
    sample_results: list[SampleEvaluation]
    overall_rubric: dict[str, Any]
    expected_overall_score: float | None
    overall_delta: float | None


def load_calibration_payload(path: Path) -> dict[str, Any]:
    """Load calibration JSON payload from disk."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, list):
        return {"samples": payload}
    if not isinstance(payload, dict):
        raise ValueError("校准文件必须是 JSON object 或 sample list")
    return payload


def evaluate_calibration(payload: dict[str, Any]) -> CalibrationReport:
    """Evaluate all samples and aggregate calibration metrics."""
    samples = payload.get("samples", [])
    if not isinstance(samples, list):
        raise ValueError("校准文件中的 samples 必须是列表")

    sample_results: list[SampleEvaluation] = []
    qa_items_for_overall: list[dict[str, Any]] = []

    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            continue

        sample_id = str(sample.get("id") or f"sample_{index}")
        rubric = evaluate_answer_rubric(
            question=str(sample.get("question", "")),
            answer=str(sample.get("answer", "")),
            analysis=_as_dict(sample.get("analysis")),
        )
        expected = _expected_answer_score(sample)
        delta = rubric["score"] - expected if expected is not None else None
        dimension_deltas = _dimension_deltas(rubric, sample)

        sample_results.append(
            SampleEvaluation(
                sample_id=sample_id,
                rubric_score=float(rubric["score"]),
                expected_score=expected,
                delta=delta,
                dimension_deltas=dimension_deltas,
                rubric=rubric,
            )
        )
        qa_items_for_overall.append({"rubric": rubric})

    overall_rubric = evaluate_overall_rubric(qa_items_for_overall, advice={})
    expected_overall_score = _expected_overall_score(payload)
    overall_delta = (
        float(overall_rubric["score"]) - expected_overall_score
        if expected_overall_score is not None
        else None
    )

    deltas = [result.delta for result in sample_results if result.delta is not None]
    scored_sample_count = len(deltas)
    mae = _mean([abs(delta) for delta in deltas])
    bias = _mean(deltas)

    return CalibrationReport(
        sample_count=len(sample_results),
        scored_sample_count=scored_sample_count,
        mae=mae,
        bias=bias,
        dimension_bias=_aggregate_dimension_bias(sample_results),
        sample_results=sample_results,
        overall_rubric=overall_rubric,
        expected_overall_score=expected_overall_score,
        overall_delta=overall_delta,
    )


def format_text_report(report: CalibrationReport) -> str:
    """Format calibration report for terminal output."""
    lines = [
        "Rubric 校准评估",
        "=" * 60,
        f"样本数: {report.sample_count}",
        f"有人工逐题分样本: {report.scored_sample_count}",
        f"逐题 MAE: {_format_optional(report.mae)}",
        f"逐题平均偏差: {_format_signed(report.bias)}",
        (
            "整体 Rubric 分: "
            f"{report.overall_rubric.get('score', '-')}, "
            f"人工期望整体分: {_format_optional(report.expected_overall_score)}, "
            f"偏差: {_format_signed(report.overall_delta)}"
        ),
        "",
        "逐题结果:",
    ]

    for result in report.sample_results:
        lines.append(
            "- "
            f"{result.sample_id}: Rubric={result.rubric_score:.1f}, "
            f"人工={_format_optional(result.expected_score)}, "
            f"偏差={_format_signed(result.delta)}"
        )

    if report.dimension_bias:
        lines.extend(["", "维度平均偏差:"])
        for key, value in report.dimension_bias.items():
            label = DIMENSION_LABELS.get(key, key)
            lines.append(f"- {label}: {_format_signed(value)}")

    return "\n".join(lines)


def report_to_json(report: CalibrationReport) -> dict[str, Any]:
    """Convert report dataclass to JSON-serializable dict."""
    return {
        "sample_count": report.sample_count,
        "scored_sample_count": report.scored_sample_count,
        "mae": report.mae,
        "bias": report.bias,
        "dimension_bias": report.dimension_bias,
        "overall_rubric": report.overall_rubric,
        "expected_overall_score": report.expected_overall_score,
        "overall_delta": report.overall_delta,
        "samples": [
            {
                "id": result.sample_id,
                "rubric_score": result.rubric_score,
                "expected_score": result.expected_score,
                "delta": result.delta,
                "dimension_deltas": result.dimension_deltas,
                "rubric": result.rubric,
            }
            for result in report.sample_results
        ],
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expected_answer_score(sample: dict[str, Any]) -> float | None:
    expected = _as_dict(sample.get("expected"))
    return _safe_float(expected.get("answer_score") or expected.get("score"))


def _expected_overall_score(payload: dict[str, Any]) -> float | None:
    overall = _as_dict(payload.get("overall"))
    return _safe_float(overall.get("expected_score") or overall.get("score"))


def _dimension_deltas(
    rubric: dict[str, Any],
    sample: dict[str, Any],
) -> dict[str, float]:
    expected_dimensions = _as_dict(_as_dict(sample.get("expected")).get("dimensions"))
    rubric_dimensions = _as_dict(rubric.get("dimensions"))
    deltas: dict[str, float] = {}
    for key, expected_value in expected_dimensions.items():
        expected_score = _safe_float(expected_value)
        rubric_score = _safe_float(_as_dict(rubric_dimensions.get(key)).get("score"))
        if expected_score is None or rubric_score is None:
            continue
        deltas[key] = rubric_score - expected_score
    return deltas


def _aggregate_dimension_bias(
    sample_results: list[SampleEvaluation],
) -> dict[str, float]:
    values_by_dimension: dict[str, list[float]] = {}
    for result in sample_results:
        for key, delta in result.dimension_deltas.items():
            values_by_dimension.setdefault(key, []).append(delta)
    return {
        key: round(sum(values) / len(values), 3)
        for key, values in values_by_dimension.items()
        if values
    }


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _format_optional(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}".rstrip("0").rstrip(".")


def _format_signed(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.3f}".rstrip("0").rstrip(".")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(description="评估 Rubric v1 与人工样本的偏差")
    parser.add_argument(
        "sample_path",
        nargs="?",
        default=str(DEFAULT_SAMPLE_PATH),
        help="校准样本 JSON 路径，默认读取 data/rubric_calibration_samples.example.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 结果，便于后续脚本处理",
    )
    parser.add_argument(
        "--max-mae",
        type=float,
        default=None,
        help="可选阈值；如果逐题 MAE 大于该值，脚本返回 1",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_arg_parser().parse_args(argv)
    payload = load_calibration_payload(Path(args.sample_path))
    report = evaluate_calibration(payload)

    if args.json:
        print(json.dumps(report_to_json(report), ensure_ascii=False, indent=2))
    else:
        print(format_text_report(report))

    if args.max_mae is not None and report.mae is not None and report.mae > args.max_mae:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
