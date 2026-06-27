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
    processing_status = Column(
        SmallInteger,
        default=0,
        comment='处理状态（0：未处理，1：正在处理，2：处理完成，3：处理失败）',
    )
    processing_tips = Column(LONGTEXT, nullable=True, comment='处理提示')
    processing_stage = Column(String(64), nullable=True, comment='处理阶段')
    processing_trace_id = Column(String(64), nullable=True, comment='任务追踪ID')
    error_code = Column(String(64), nullable=True, comment='错误代码')
    error_type = Column(String(32), nullable=True, comment='错误类型')
    error_message = Column(LONGTEXT, nullable=True, comment='错误信息')
    retry_count = Column(Integer, nullable=True, default=0, comment='当前重试次数')
    max_retries = Column(Integer, nullable=True, comment='最大重试次数')
    failed_at = Column(DateTime, nullable=True, comment='失败时间')
    processing_started_at = Column(DateTime, nullable=True, comment='开始处理时间')
    stage_started_at = Column(DateTime, nullable=True, comment='当前阶段开始时间')
    last_progress_at = Column(DateTime, nullable=True, comment='最近进度更新时间')
    completed_at = Column(DateTime, nullable=True, comment='完成时间')
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
