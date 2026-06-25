from sqlalchemy import Column, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT

from .base import Base


class TbInterviewExtractCache(Base):
    __tablename__ = 'tb_interview_extract_cache'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='唯一标识ID')
    record_id = Column(Integer, nullable=False, unique=True, comment='面试记录ID')
    qa_json = Column(LONGTEXT, nullable=False, comment='Q&A 抽取结果(JSON字符串)')
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    update_time = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment='修改时间',
    )

    __table_args__ = (
        UniqueConstraint('record_id', name='uk_extract_record_id'),
    )
