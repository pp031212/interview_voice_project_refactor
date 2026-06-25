from typing import TypedDict, List


class InterViewInfoDict(TypedDict):
    # 姓名
    name: str
    # 所在公司
    company: str
    # 所在职位
    subject: str
    # 面试时间
    interview_date_str: str


class AgentState(TypedDict):
    # 面试基础信息
    interview_info_dict: InterViewInfoDict
    # 输入语音的路径
    input_audio_path: str
    # 分割后的音频文件路径
    split_audio_path_list: List[str]
    # 分割后语音识别的文本
    voice_text_list: List[str]
    # 整理后的语音识别的文本
    voice_arrange_text: str
    # 抽取面试题
    interview_topic_list: List[dict]
    # 抽取面试题的答案
    interview_advice: dict
    # 抽取面试题的markdown信息
    interview_markdown_text: str
    # 录音的id
    record_id: int
