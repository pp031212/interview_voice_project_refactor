from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


RUBRIC_VERSION = "rubric_v1"


@dataclass(frozen=True)
class DimensionScore:
    """Single rubric dimension score."""

    score: float
    weight: float
    reason: str


DIMENSION_WEIGHTS: dict[str, float] = {
    "relevance": 0.15,
    "technical_accuracy": 0.30,
    "completeness": 0.20,
    "depth_evidence": 0.20,
    "structure": 0.10,
    "professional_credibility": 0.05,
}

INTENT_EXPECTED_POINTS: dict[str, list[str]] = {
    "self_introduction": ["基本背景", "技术方向", "项目经验", "岗位匹配"],
    "project_experience": ["项目背景", "个人职责", "技术方案", "结果或产出"],
    "technical_solution": ["关键步骤", "技术方案", "原因或取舍", "结果验证"],
    "comparison_reasoning": ["对比对象", "优势原因", "限制条件", "适用场景"],
    "confirmation_boundary": ["直接确认", "具体范围", "职责边界", "补充说明"],
    "candidate_questions": ["岗位问题", "团队或业务问题", "后续确认"],
    "general": ["直接回答", "关键事实", "示例或证据"],
}

COVERAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "基本背景": ("毕业", "专业", "学校", "背景", "经历", "我叫"),
    "技术方向": ("技术", "方向", "算法", "模型", "开发", "工程", "RAG", "Agent"),
    "项目经验": ("项目", "参与", "负责", "开发", "实践", "经验"),
    "岗位匹配": ("岗位", "业务", "公司", "匹配", "希望", "适合"),
    "项目背景": ("项目", "系统", "平台", "业务", "场景", "问题"),
    "个人职责": ("负责", "参与", "主导", "协助", "我的", "工作", "模块"),
    "技术方案": ("方案", "使用", "采用", "实现", "架构", "模型", "数据库", "接口"),
    "结果或产出": ("提升", "降低", "完成", "上线", "产出", "结果", "效果", "%"),
    "关键步骤": ("先", "然后", "最后", "步骤", "流程", "第一", "第二"),
    "原因或取舍": ("因为", "所以", "取舍", "原因", "考虑", "优势", "缺点"),
    "结果验证": ("验证", "测试", "指标", "准确率", "召回", "效果", "数据"),
    "对比对象": ("相比", "对比", "区别", "不同", "直接", "传统"),
    "优势原因": ("优势", "好处", "提升", "避免", "减少", "更"),
    "限制条件": ("限制", "前提", "条件", "不足", "风险", "但是"),
    "适用场景": ("适合", "场景", "应用", "用户", "业务"),
    "直接确认": ("是", "不是", "有", "没有", "不涉及", "确认"),
    "具体范围": ("主要", "包括", "范围", "部分", "模块", "环节"),
    "职责边界": ("不属于", "未参与", "边界", "只负责", "协助", "基础"),
    "补充说明": ("补充", "另外", "同时", "但", "不过"),
    "岗位问题": ("岗位", "职责", "业务", "方向", "要求"),
    "团队或业务问题": ("团队", "规模", "业务", "客户", "产品"),
    "后续确认": ("请问", "是否", "如何", "支持", "具体"),
    "直接回答": ("是", "有", "没有", "可以", "主要", "通过", "采用"),
    "关键事实": ("负责", "项目", "数据", "系统", "模型", "用户", "公司"),
    "示例或证据": ("例如", "比如", "以", "数据", "指标", "结果", "案例"),
}

TECHNICAL_TERMS = (
    "RAG",
    "Agent",
    "SQL",
    "Python",
    "Docker",
    "API",
    "向量",
    "知识库",
    "知识图谱",
    "模型",
    "架构",
    "数据库",
    "检索",
    "意图识别",
    "实体",
    "接口",
)

POSITIVE_ACCURACY_SIGNALS = ("准确", "正确", "合理", "清晰", "符合", "具体", "较好")
NEGATIVE_ACCURACY_SIGNALS = (
    "错误",
    "不准确",
    "不符合",
    "含糊",
    "笼统",
    "缺乏",
    "不足",
    "跑题",
)


def evaluate_answer_rubric(
    question: str,
    answer: str,
    analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one interview answer with deterministic rubric v1.

    The LLM's existing analysis is used only as weak context. Final dimension
    scores are calculated locally with fixed weights.
    """
    normalized_question = _normalize_text(question)
    normalized_answer = _normalize_text(answer)
    normalized_analysis = analysis if isinstance(analysis, dict) else {}

    intent = classify_question_intent(normalized_question)
    expected_points = _build_expected_points(intent, normalized_analysis)
    answer_evidence = _extract_answer_evidence(normalized_answer, expected_points)
    missing_points = [
        point for point in expected_points if not _point_covered(point, normalized_answer)
    ]
    off_topic_content = _detect_off_topic_content(normalized_question, normalized_answer)

    if not normalized_answer:
        dimensions = {
            key: DimensionScore(0.0, weight, "未检测到回答内容")
            for key, weight in DIMENSION_WEIGHTS.items()
        }
    else:
        dimensions = {
            "relevance": _score_relevance(
                normalized_question,
                normalized_answer,
                expected_points,
                missing_points,
                off_topic_content,
            ),
            "technical_accuracy": _score_technical_accuracy(
                normalized_answer,
                normalized_analysis,
            ),
            "completeness": _score_completeness(expected_points, missing_points),
            "depth_evidence": _score_depth_evidence(normalized_answer),
            "structure": _score_structure(normalized_answer),
            "professional_credibility": _score_professional_credibility(
                normalized_answer
            ),
        }

    weighted_score = sum(
        dimension.score * dimension.weight for dimension in dimensions.values()
    )

    return {
        "version": RUBRIC_VERSION,
        "score": round(_clamp(weighted_score), 1),
        "question_intent": intent,
        "expected_points": expected_points,
        "answer_evidence": answer_evidence,
        "missing_points": missing_points,
        "off_topic_content": off_topic_content,
        "dimensions": {
            key: {
                "score": round(value.score, 1),
                "weight": value.weight,
                "reason": value.reason,
            }
            for key, value in dimensions.items()
        },
    }


def classify_question_intent(question: str) -> str:
    """Classify question into a stable coarse intent."""
    if any(keyword in question for keyword in ("自我介绍", "介绍一下", "背景")):
        return "self_introduction"
    if any(keyword in question for keyword in ("有何疑问", "有什么问题", "想问")):
        return "candidate_questions"
    if any(keyword in question for keyword in ("是否", "有没有", "是不是", "涉及")):
        return "confirmation_boundary"
    if any(keyword in question for keyword in ("相比", "对比", "优势", "区别")):
        return "comparison_reasoning"
    if any(keyword in question for keyword in ("几个项目", "项目", "经历", "负责")):
        return "project_experience"
    if any(keyword in question for keyword in ("如何", "怎么", "流程", "实现", "架构")):
        return "technical_solution"
    return "general"


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _build_expected_points(intent: str, analysis: dict[str, Any]) -> list[str]:
    expected_points = list(
        INTENT_EXPECTED_POINTS.get(intent, INTENT_EXPECTED_POINTS["general"])
    )
    extracted_points = _extract_numbered_points(str(analysis.get("answer_approach", "")))
    for point in extracted_points:
        if point not in expected_points:
            expected_points.append(point)
    return expected_points[:6]


def _extract_numbered_points(text: str) -> list[str]:
    if not text:
        return []

    candidates = re.split(r"[；;。]\s*|\d+[.)、]\s*", text)
    points: list[str] = []
    for candidate in candidates:
        cleaned = candidate.strip(" ：:，,。；;")
        if 2 <= len(cleaned) <= 24:
            points.append(cleaned)
    return points[:3]


def _point_covered(point: str, answer: str) -> bool:
    aliases = COVERAGE_ALIASES.get(point, ())
    if aliases:
        return any(alias in answer for alias in aliases)

    point_tokens = _extract_keywords(point)
    return bool(point_tokens) and any(token in answer for token in point_tokens)


def _extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_+#.-]{2,}|[\u4e00-\u9fff]{2,}", text)
    return [token for token in tokens if token not in {"应该", "包括", "说明"}]


def _extract_answer_evidence(answer: str, expected_points: list[str]) -> list[str]:
    sentences = [
        item.strip()
        for item in re.split(r"[。！？!?；;]\s*", answer)
        if item.strip()
    ]
    if not sentences and answer:
        sentences = [answer]

    evidence: list[str] = []
    for sentence in sentences:
        if len(evidence) >= 3:
            break
        if any(_point_covered(point, sentence) for point in expected_points):
            evidence.append(sentence[:80])

    if not evidence and sentences:
        evidence.append(sentences[0][:80])
    return evidence


def _detect_off_topic_content(question: str, answer: str) -> list[str]:
    if not answer:
        return []
    if any(keyword in answer for keyword in ("不知道", "不清楚", "不了解")):
        return ["回答明确表示不了解，需人工判断是否属于合理边界"]

    question_keywords = set(_extract_keywords(question))
    answer_keywords = set(_extract_keywords(answer))
    if question_keywords and answer_keywords and question_keywords.isdisjoint(
        answer_keywords
    ):
        if len(answer) > 40:
            return ["回答与问题关键词重合度较低"]
    return []


def _score_relevance(
    question: str,
    answer: str,
    expected_points: list[str],
    missing_points: list[str],
    off_topic_content: list[str],
) -> DimensionScore:
    covered_count = max(len(expected_points) - len(missing_points), 0)
    coverage_ratio = covered_count / max(len(expected_points), 1)
    direct_answered = _is_directly_answered(question, answer)

    score = (4.0 if direct_answered else 1.5) + 5.0 * coverage_ratio
    if off_topic_content:
        score -= 2.0

    reason = f"覆盖关键点 {covered_count}/{len(expected_points)}"
    if direct_answered:
        reason += "，回答正面回应问题"
    if off_topic_content:
        reason += "，存在疑似跑题内容"
    return DimensionScore(_clamp(score), DIMENSION_WEIGHTS["relevance"], reason)


def _is_directly_answered(question: str, answer: str) -> bool:
    if any(keyword in question for keyword in ("是否", "有没有", "是不是", "涉及")):
        return any(keyword in answer for keyword in ("是", "不是", "有", "没有", "不涉及"))

    question_keywords = set(_extract_keywords(question))
    answer_keywords = set(_extract_keywords(answer))
    if not question_keywords:
        return bool(answer)
    return bool(question_keywords.intersection(answer_keywords)) or len(answer) >= 30


def _score_technical_accuracy(
    answer: str,
    analysis: dict[str, Any],
) -> DimensionScore:
    evaluation_text = str(analysis.get("answer_evaluation", ""))
    positive_count = sum(
        signal in evaluation_text for signal in POSITIVE_ACCURACY_SIGNALS
    )
    negative_count = sum(
        signal in evaluation_text for signal in NEGATIVE_ACCURACY_SIGNALS
    )
    technical_term_count = sum(term in answer for term in TECHNICAL_TERMS)

    score = 5.5 + min(technical_term_count, 4) * 0.6
    score += min(positive_count, 2) * 0.7
    score -= min(negative_count, 3) * 1.0

    if any(keyword in answer for keyword in ("不知道", "不清楚", "不了解")):
        score = min(score, 4.0)

    reason = f"检测到技术关键词 {technical_term_count} 个"
    if negative_count:
        reason += f"，评价文本含 {negative_count} 个准确性风险信号"
    return DimensionScore(
        _clamp(score),
        DIMENSION_WEIGHTS["technical_accuracy"],
        reason,
    )


def _score_completeness(
    expected_points: list[str],
    missing_points: list[str],
) -> DimensionScore:
    covered_count = max(len(expected_points) - len(missing_points), 0)
    coverage_ratio = covered_count / max(len(expected_points), 1)
    score = 2.0 + 8.0 * coverage_ratio
    reason = f"期望覆盖点完成 {covered_count}/{len(expected_points)}"
    if missing_points:
        reason += "，缺失：" + "、".join(missing_points[:3])
    return DimensionScore(_clamp(score), DIMENSION_WEIGHTS["completeness"], reason)


def _score_depth_evidence(answer: str) -> DimensionScore:
    evidence_markers = 0
    evidence_markers += len(re.findall(r"\d+|%|百分", answer))
    evidence_markers += sum(
        keyword in answer
        for keyword in ("例如", "比如", "以", "负责", "实现", "提升", "降低")
    )
    evidence_markers += sum(term in answer for term in TECHNICAL_TERMS)

    length_bonus = 2.0 if len(answer) >= 120 else 1.0 if len(answer) >= 60 else 0.0
    score = 3.0 + min(evidence_markers, 6) * 0.9 + length_bonus
    reason = f"检测到证据/细节信号 {evidence_markers} 个"
    return DimensionScore(_clamp(score), DIMENSION_WEIGHTS["depth_evidence"], reason)


def _score_structure(answer: str) -> DimensionScore:
    connector_count = sum(
        keyword in answer
        for keyword in ("首先", "其次", "然后", "最后", "第一", "第二", "主要", "同时", "因此")
    )
    sentence_count = len(
        [item for item in re.split(r"[。！？!?；;]", answer) if item.strip()]
    )
    score = 4.0 + min(connector_count, 3) * 1.2 + min(sentence_count, 4) * 0.6
    if len(answer) < 20:
        score -= 2.0
    reason = f"结构连接词 {connector_count} 个，句段 {sentence_count} 个"
    return DimensionScore(_clamp(score), DIMENSION_WEIGHTS["structure"], reason)


def _score_professional_credibility(answer: str) -> DimensionScore:
    boundary_count = sum(
        keyword in answer
        for keyword in ("负责", "参与", "协助", "不属于", "未参与", "主要", "基础", "边界")
    )
    overclaim_count = sum(
        keyword in answer for keyword in ("全部负责", "完全精通", "百分之百", "所有模块")
    )
    score = 6.0 + min(boundary_count, 3) * 0.8 - overclaim_count * 1.5
    reason = f"职责/边界表达信号 {boundary_count} 个"
    if overclaim_count:
        reason += f"，存在 {overclaim_count} 个疑似夸大信号"
    return DimensionScore(
        _clamp(score),
        DIMENSION_WEIGHTS["professional_credibility"],
        reason,
    )


def _clamp(value: float, lower: float = 0.0, upper: float = 10.0) -> float:
    return max(lower, min(upper, value))
