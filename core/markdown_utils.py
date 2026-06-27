import ast
import json


def literal_eval(str_data):
    try:
        return ast.literal_eval(str_data)
    except Exception:
        return []


def parse_json(str_data):
    try:
        return json.loads(str_data or "{}")
    except Exception:
        return {}


def format_rubric_summary(rubric):
    if not isinstance(rubric, dict) or not rubric:
        return []

    md_parts = [f"  - **Rubric v1旁路评分**：{rubric.get('score', '')}\n"]
    dimensions = rubric.get("dimensions", {})
    if isinstance(dimensions, dict):
        labels = {
            "relevance": "相关性",
            "technical_accuracy": "技术准确性",
            "completeness": "完整度",
            "depth_evidence": "深度与证据",
            "structure": "表达结构",
            "professional_credibility": "职业可信度",
        }
        dimension_text = []
        for key, label in labels.items():
            item = dimensions.get(key, {})
            if isinstance(item, dict):
                dimension_text.append(f"{label} {item.get('score', '-')}")
        if dimension_text:
            md_parts.append(f"  - **Rubric维度**：{'；'.join(dimension_text)}\n")

    missing_points = rubric.get("missing_points", [])
    if isinstance(missing_points, list) and missing_points:
        md_parts.append(f"  - **Rubric缺失点**：{'；'.join(map(str, missing_points[:3]))}\n")
    return md_parts


def generate_markdown(records, detail_list):
    if len(records) <= 0:
        return ""
    name = records[0].get("name", "")
    interview_date_str = str(records[0].get("interview_time", ""))
    overall_comment = records[0].get("overall_comments", "")
    overall_score = records[0].get("interview_score", 0.0)
    strengths = literal_eval(records[0].get("strengths", ""))
    weaknesses = literal_eval(records[0].get("weaknesses", ""))
    improvements_suggestions = literal_eval(records[0].get("improvement_suggestions", ""))

    md_parts = []
    md_parts.append(f"# {name}同学面试复盘报告\n")
    md_parts.append(f"### 面试时间:{interview_date_str}")

    md_parts.append("## 一、面试表现分析与建议\n")

    md_parts.append("### 1、整体点评：\n")
    md_parts.append(f"\n{overall_comment}\n")

    md_parts.append("### 2、整体评分：\n")
    md_parts.append(f"\n{overall_score}\n")

    md_parts.append("### 3、优势:\n")
    for strength in strengths:
        md_parts.append(f"- {strength}")

    md_parts.append("### 4、不足: \n")
    for weakness in weaknesses:
        md_parts.append(f"- {weakness}")

    md_parts.append("### 5、改进建议：\n")
    for suggestion in improvements_suggestions:
        md_parts.append(f"- {suggestion}")

    md_parts.append("## 二、面试问答记录\n")
    for idx, qa in enumerate(detail_list, 1):
        interview_question = qa.get("interview_question", "")
        interviewee_answer = qa.get("interviewee_answer", "")
        reference_answer = qa.get("reference_answer", "")
        point_analysis = qa.get("point_analysis", "")
        answer_thoughts = qa.get("answer_thoughts", "")
        answer_evaluation = qa.get("answer_evaluation", "")
        answer_score = qa.get("answer_score", 0.0)
        rubric = parse_json(qa.get("rubric_json", ""))

        md_parts.append(f"### 问题 {idx}: {interview_question}\n")
        md_parts.append(f"- **面试者回答**：\n\n{interviewee_answer}\n")
        md_parts.append(f"- **参考答案**：\n\n{reference_answer}\n")

        md_parts.append("- **面试题分析**：\n")
        md_parts.append(f"  - **考点分析**：{point_analysis}\n")
        md_parts.append(f"  - **答题思路**：{answer_thoughts}\n")
        md_parts.append(f"  - **回答评价**：{answer_evaluation}\n")
        md_parts.append(f"  - **模型回答评分**：{answer_score}\n")
        md_parts.extend(format_rubric_summary(rubric))

    return "\n".join(md_parts)
