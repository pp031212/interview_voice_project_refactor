from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func

from infra.db.model.base import Base


class TbUser(Base):
    __tablename__ = 'tb_user'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='唯一标识ID')
    user_id = Column(String(32), nullable=False, comment='用户ID')
    user_name = Column(String(32), nullable=True, comment='用户名称')
    user_pwd = Column(String(32), nullable=True, comment='用户密码')

    create_time = Column(DateTime, default=func.now(), comment='创建时间')
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='修改时间')
