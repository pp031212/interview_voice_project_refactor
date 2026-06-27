from scripts.evaluate_rubric_calibration import (
    evaluate_calibration,
    format_text_report,
    report_to_json,
)


def test_evaluate_calibration_computes_mae_and_bias() -> None:
    payload = {
        "samples": [
            {
                "id": "sample_a",
                "question": "你主要负责哪些工作？",
                "answer": "我主要负责数据清洗、SQL模块和RAG集成。",
                "analysis": {
                    "answer_evaluation": "回答具体，职责边界清晰。",
                },
                "expected": {
                    "answer_score": 7.0,
                    "dimensions": {"relevance": 7.5},
                },
            },
            {
                "id": "sample_b",
                "question": "该流程有什么优势？",
                "answer": "可以动态更新知识并减少幻觉。",
                "expected": {"answer_score": 6.0},
            },
        ],
        "overall": {"expected_score": 6.5},
    }

    report = evaluate_calibration(payload)

    assert report.sample_count == 2
    assert report.scored_sample_count == 2
    assert report.mae is not None
    assert report.bias is not None
    assert report.expected_overall_score == 6.5
    assert report.overall_delta is not None
    assert "relevance" in report.dimension_bias


def test_report_formatters_return_expected_shape() -> None:
    payload = {
        "samples": [
            {
                "id": "sample_a",
                "question": "是否参与部署？",
                "answer": "没有参与部署，我主要负责基础数据处理。",
                "expected": {"answer_score": 6.0},
            }
        ]
    }
    report = evaluate_calibration(payload)

    text = format_text_report(report)
    data = report_to_json(report)

    assert "Rubric 校准评估" in text
    assert data["sample_count"] == 1
    assert data["samples"][0]["id"] == "sample_a"
