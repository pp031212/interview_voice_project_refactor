from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.schema import Index

from infra.db.model.base import Base


class TbAsrSegmentCache(Base):
    __tablename__ = "tb_asr_segment_cache"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="唯一标识ID")
    record_id = Column(Integer, nullable=False, comment="面试记录ID")
    segment_index = Column(Integer, nullable=False, comment="音频分片序号（从0开始）")
    segment_path = Column(String(1024), nullable=False, comment="音频分片路径")
    segment_text = Column(LONGTEXT, nullable=False, comment="ASR识别文本")
    create_time = Column(DateTime, default=func.now(), comment="创建时间")
    update_time = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="修改时间"
    )

    __table_args__ = (
        UniqueConstraint("record_id", "segment_index", name="uk_record_segment"),
        Index("ind_record_id", "record_id"),
    )
