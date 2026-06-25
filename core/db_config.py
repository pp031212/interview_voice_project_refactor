from __future__ import annotations

from dataclasses import dataclass

from core.config import get_config


@dataclass(frozen=True)
class DbConfig:
    mysql_host: str | None
    mysql_port: int
    mysql_user: str | None
    mysql_password: str | None
    mysql_database_name: str | None


def get_db_config() -> DbConfig:
    config = get_config()
    return DbConfig(
        mysql_host=config.mysql_host,
        mysql_port=config.mysql_port,
        mysql_user=config.mysql_user,
        mysql_password=config.mysql_password,
        mysql_database_name=config.mysql_database_name,
    )
