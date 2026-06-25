from sqlalchemy import Column, DateTime, Integer, text
from sqlalchemy.dialects.mysql import LONGTEXT

from infra.db.model.base import Base


class TbInterviewAnalysisCache(Base):
    __tablename__ = "tb_interview_analysis_cache"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="唯一标识ID")
    record_id = Column(Integer, nullable=False, index=True, comment="面试记录ID")
    qa_index = Column(Integer, nullable=False, comment="问答序号（从0开始）")
    qa_json = Column(LONGTEXT, nullable=False, comment="逐题分析结果(JSON字符串)")
    create_time = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="创建时间",
    )
    update_time = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        nullable=False,
        comment="修改时间",
    )
