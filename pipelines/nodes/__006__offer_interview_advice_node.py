import sys
import os
import json

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pydantic import BaseModel, Field  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langchain_core.output_parsers import JsonOutputParser  # noqa: E402
from pipelines.agent_state import AgentState  # noqa: E402
from infra.update_mysql import update_mysql  # noqa: E402
from core.llm import get_report_llm  # noqa: E402
from core.llm_output_utils import extract_json_payload  # noqa: E402
from core.rubric import evaluate_overall_rubric  # noqa: E402
from infra.db.db_helper import my_db_helper  # noqa: E402


# 定义 Pydantic schema
class InterviewAdvice(BaseModel):
    overall_comment: str = Field(description="对整体面试表现的点评")
    overall_score: float = Field(description="面试整体评分，满分10分")
    strengths: list[str] = Field(description="面试者的优势点")
    weaknesses: list[str] = Field(description="面试者的不足之处")
    suggestions: list[str] = Field(description="改进建议")


parser = JsonOutputParser(pydantic_object=InterviewAdvice)


def _build_fallback_advice() -> dict:
    return {
        "overall_comment": "模型未返回可解析的结构化总评，建议人工复核整场面试反馈。",
        "overall_score": 0.0,
        "strengths": [],
        "weaknesses": ["模型输出非 JSON，已启用保底结果避免流程中断。"],
        "suggestions": ["建议重试该记录或切换模型后重新生成总评。"],
    }


def _normalize_advice(result: dict) -> dict:
    if not isinstance(result, dict):
        return _build_fallback_advice()

    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    strengths = result.get("strengths", [])
    weaknesses = result.get("weaknesses", [])
    suggestions = result.get("suggestions", [])

    if not isinstance(strengths, list):
        strengths = [str(strengths)] if strengths else []
    if not isinstance(weaknesses, list):
        weaknesses = [str(weaknesses)] if weaknesses else []
    if not isinstance(suggestions, list):
        suggestions = [str(suggestions)] if suggestions else []

    return {
        "overall_comment": str(result.get("overall_comment", "")),
        "overall_score": _safe_float(result.get("overall_score", 0.0), 0.0),
        "strengths": [str(x) for x in strengths],
        "weaknesses": [str(x) for x in weaknesses],
        "suggestions": [str(x) for x in suggestions],
    }


def _overall_rubric_score(overall_rubric: dict) -> float | None:
    try:
        return float(overall_rubric.get("score"))
    except (TypeError, ValueError):
        return None


def _overall_rubric_json(overall_rubric: dict) -> str | None:
    if not isinstance(overall_rubric, dict) or not overall_rubric:
        return None
    return json.dumps(overall_rubric, ensure_ascii=False)


async def offer_interview_advice_node(state: AgentState):
    await update_mysql("开始提供面试建议", record_id=state["record_id"])
    voice_arrange_text = state["voice_arrange_text"]

    parser = JsonOutputParser(pydantic_object=InterviewAdvice)
    format_instructions = parser.get_format_instructions()

    # ⚠️ system 里必须直接给出 parser 的 format 指令
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是一位专业的面试辅导专家。\n"
         "以下是一次面试的语音转文字逐字稿，因此可能包含口头禅、停顿词和语气词。\n"
         "请结合这一点进行分析，但重点放在内容本身，而不是转写的噪音。\n"
         "评分标准：整体评分为0到10分，10分代表表现极佳，0分代表非常糟糕。"
         "请严格输出符合以下 JSON schema 的内容，不要多余解释：\n\n"
         "{format_instructions}"),
        ("human",
         "以下是一次完整的面试逐字稿（语音转文字）：\n\n{interview_text}\n\n"
         "请你根据 schema 生成 JSON 格式的面试反馈。")
    ]).partial(format_instructions=format_instructions)

    # 不使用 response_format 强约束，统一走通用解析修复链路。
    report_llm = get_report_llm()
    print("ℹ️ 总评节点使用通用解析修复链路")

    # 只能对 LLM 部分 stream，parser 不支持流式解析
    llm_chain = prompt | report_llm

    print("\n=== 流式输出开始 ===\n")
    payload = {"interview_text": voice_arrange_text}
    chunks = []
    for chunk in llm_chain.stream(payload):
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        print(content, end="", flush=True)
        chunks.append(content)
    print("\n\n=== 流式输出结束 ===\n")

    full_output = "".join(chunks).strip()

    try:
        advice_dict = parser.parse(full_output)
    except Exception as e:
        print(f"⚠️ 面试总评 JSON 解析失败，尝试修复: {e}")
        try:
            advice_dict = parser.parse(extract_json_payload(full_output))
            print("✓ 总评 JSON 修复成功")
        except Exception as e2:
            print(f"❌ 总评 JSON 修复失败: {e2}")
            advice_dict = _build_fallback_advice()
            print("⚠️ 已使用总评保底结果继续处理，避免流程中断。")

    advice_dict = _normalize_advice(advice_dict)
    overall_rubric = evaluate_overall_rubric(
        state.get("interview_topic_list", []),
        advice_dict,
    )
    advice_dict["overall_rubric"] = overall_rubric
    print(advice_dict)

    state["interview_advice"] = advice_dict
    await update_mysql("完成提供面试建议", record_id=state["record_id"])
    overall_comments = advice_dict.get("overall_comment", "")
    overall_score = advice_dict.get("overall_score", 0.0)
    strengths = str(advice_dict.get("strengths", []))
    weaknesses = str(advice_dict.get("weaknesses", []))
    improvement_suggestions = str(advice_dict.get("suggestions", []))
    my_db_helper.update_interview_record(
        state["record_id"],
        {
            "overall_comments": overall_comments,
            "interview_score": overall_score,
            "overall_rubric_score": _overall_rubric_score(overall_rubric),
            "overall_rubric_json": _overall_rubric_json(overall_rubric),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvement_suggestions": improvement_suggestions,
        },
    )
    return state


if __name__ == '__main__':
    import asyncio

    asyncio.run(
        offer_interview_advice_node({"record_id": 3,
                                     "voice_arrange_text": ""}))
