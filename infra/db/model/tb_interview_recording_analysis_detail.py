from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql import func

from infra.db.model.base import Base


class TbInterviewRecordingAnalysisDetail(Base):
    __tablename__ = 'tb_interview_recording_analysis_detail'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='唯一标识ID')
    interview_record_analysis_id = Column(String(32), nullable=False, comment='面试记录分析ID')
    interview_question = Column(Text, nullable=True, comment='面试问题')
    interviewee_answer = Column(Text, nullable=True, comment='面试者回答')
    reference_answer = Column(Text, nullable=True, comment='参考答案')
    point_analysis = Column(Text, nullable=True, comment='考点分析')
    answer_thoughts = Column(Text, nullable=True, comment='答题思路')
    answer_evaluation = Column(Text, nullable=True, comment='回答评价')
    answer_score = Column(Float, nullable=True, comment='回答评分')
    rubric_score = Column(Float, nullable=True, comment='Rubric评分')
    rubric_json = Column(LONGTEXT, nullable=True, comment='Rubric评分详情JSON')

    # 创建时间
    create_time = Column(DateTime, default=func.now(), comment='创建时间')
    # 修改时间
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='修改时间')
