from core.rubric import (
    OVERALL_RUBRIC_VERSION,
    RUBRIC_VERSION,
    classify_question_intent,
    evaluate_answer_rubric,
    evaluate_overall_rubric,
)


def test_classify_question_intent_project_experience() -> None:
    assert classify_question_intent("你主要负责哪个项目？") == "project_experience"


def test_classify_question_intent_confirmation_before_project() -> None:
    assert (
        classify_question_intent("运动医学知识图谱项目是否涉及语音对话？")
        == "confirmation_boundary"
    )


def test_evaluate_answer_rubric_returns_stable_shape() -> None:
    result = evaluate_answer_rubric(
        question="该项目团队规模如何？你主要负责哪些部分？",
        answer=(
            "团队共有6人。我主要负责数据清洗、SQL模块和RAG集成，"
            "并协助意图识别模块的工作。"
        ),
        analysis={
            "answer_approach": "应说明团队规模、个人职责、技术方案和项目产出。",
            "answer_evaluation": "回答具体，职责边界清晰。",
        },
    )

    assert result["version"] == RUBRIC_VERSION
    assert 0 <= result["score"] <= 10
    assert result["question_intent"] == "project_experience"
    assert result["answer_evidence"]
    assert set(result["dimensions"]) == {
        "relevance",
        "technical_accuracy",
        "completeness",
        "depth_evidence",
        "structure",
        "professional_credibility",
    }


def test_evaluate_overall_rubric_aggregates_question_scores() -> None:
    qa_items = [
        {
            "rubric": evaluate_answer_rubric(
                question="该项目团队规模如何？你主要负责哪些部分？",
                answer="团队共有6人，我主要负责数据清洗、SQL模块和RAG集成。",
                analysis={
                    "answer_evaluation": "回答具体，职责边界清晰。",
                },
            )
        },
        {
            "rubric": evaluate_answer_rubric(
                question="该流程与直接使用DeepSeek相比有何优势？",
                answer="知识图谱可动态更新规则，减少大模型幻觉并提升准确性。",
                analysis={
                    "answer_evaluation": "回答准确，但适用场景说明略少。",
                },
            )
        },
    ]

    result = evaluate_overall_rubric(
        qa_items,
        advice={"weaknesses": ["技术细节仍可补充"]},
    )

    assert result["version"] == OVERALL_RUBRIC_VERSION
    assert 0 <= result["score"] <= 10
    assert len(result["question_scores"]) == 2
    assert set(result["components"]) == {
        "question_average",
        "expression_consistency",
        "job_fit",
        "risk_adjustment",
    }
