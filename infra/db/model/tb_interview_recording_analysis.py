from sqlalchemy import Column, String, Integer, Float, DateTime, SmallInteger, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.schema import Index

from infra.db.model.base import Base


class TbInterviewRecordingAnalysis(Base):
    __tablename__ = 'tb_interview_recording_analysis'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='唯一标识ID')
    name = Column(String(100), nullable=False, comment='姓名')
    interview_time = Column(DateTime, nullable=False, comment='面试时间')
    company_name = Column(String(255), nullable=False, comment='公司名')
    subject = Column(String(255), nullable=True, comment='面试学科')
    recording_url = Column(String(255), nullable=False, comment='录音地址')
    processing_status = Column(SmallInteger, default=0, comment='处理进度（0：未处理，1：正在处理，2：处理完成）')
    processing_tips = Column(LONGTEXT, nullable=True, comment='处理提示')
    overall_comments = Column(LONGTEXT, nullable=True, comment='整体点评')
    interview_score = Column(Float, nullable=True, comment='面试评分')
    strengths = Column(LONGTEXT, nullable=True, comment='优势点')
    weaknesses = Column(LONGTEXT, nullable=True, comment='不足点')
    improvement_suggestions = Column(LONGTEXT, nullable=True, comment='改进建议')
    interview_text = Column(LONGTEXT, nullable=True, comment='面试文本')
    markdown_text = Column(LONGTEXT, nullable=True, comment='面试评价格式生成')

    create_time = Column(DateTime, default=func.now(), comment='创建时间')
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='修改时间')

    __table_args__ = (
        Index('ind_name', 'name'),
    )
