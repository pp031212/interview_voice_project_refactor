from __future__ import annotations

import json

from datetime import datetime

from sqlalchemy import create_engine, desc, text
from sqlalchemy.orm import sessionmaker

from core.db_config import DbConfig, get_db_config
from core.errors import DatabaseError, RecordNotFoundError
from core.task_status import InterviewProcessingStatus
from infra.db.model.base import Base
from infra.db.model.tb_interview_recording_analysis import TbInterviewRecordingAnalysis
from infra.db.model.tb_interview_recording_analysis_detail import (
    TbInterviewRecordingAnalysisDetail,
)
from infra.db.model.tb_asr_segment_cache import TbAsrSegmentCache
from infra.db.model.tb_interview_extract_cache import TbInterviewExtractCache
from infra.db.model.tb_interview_analysis_cache import TbInterviewAnalysisCache
from infra.db.model.tb_user import TbUser


class DatabaseHelper:
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        Session = sessionmaker(bind=self.engine)
        self.Session = Session
        self._tables_created = False

    def _ensure_tables_created(self) -> None:
        if not self._tables_created:
            try:
                Base.metadata.create_all(self.engine)
                self._tables_created = True
            except Exception as exc:
                print(f"警告: 创建数据库表时出错: {exc}")
                print("提示: 请确保 MySQL 服务已启动，并且配置正确")
                raise DatabaseError(f"创建数据库表失败: {str(exc)}")

    def _check_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            print(f"数据库连接失败: {exc}")
            return False

    def get_user_by_id(self, user_id: str) -> TbUser | None:
        """根据用户 ID 查询用户。

        Args:
            user_id: 用户 ID。

        Returns:
            TbUser | None: 找到返回用户对象，未找到返回 None。

        Raises:
            DatabaseError: 查询失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            user = session.query(TbUser).filter(TbUser.user_id == user_id).first()
            return user
        except Exception as exc:
            raise DatabaseError(f"查询用户失败: {str(exc)}")
        finally:
            session.close()

    def add_interview_record(
        self,
        name: str,
        interview_time: datetime | None = None,
        company_name: str | None = None,
        recording_url: str | None = None,
        subject: str | None = None,
    ) -> int:
        """添加面试记录。

        Args:
            name: 姓名。
            interview_time: 面试时间，默认为当前时间。
            company_name: 公司名称，默认为"未知公司"。
            recording_url: 录音地址，默认为空字符串。
            subject: 学科，默认为"未知学科"。

        Returns:
            int: 新记录的 ID。

        Raises:
            DatabaseError: 添加失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            if interview_time is None:
                interview_time = datetime.now()
            if company_name is None or company_name == "":
                company_name = "未知公司"
            if recording_url is None:
                recording_url = ""
            if subject is None or subject == "":
                subject = "未知学科"
            processing_status = InterviewProcessingStatus.PENDING

            new_record = TbInterviewRecordingAnalysis(
                name=name,
                interview_time=interview_time,
                company_name=company_name,
                recording_url=recording_url,
                processing_status=processing_status,
                subject=subject,
            )

            session.add(new_record)
            session.commit()

            return new_record.id
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"添加面试记录失败: {str(exc)}")
        finally:
            session.close()

    def update_interview_record(self, record_id: int | str, update_fields: dict) -> bool:
        """更新面试记录。

        Args:
            record_id: 面试记录 ID。
            update_fields: 要更新的字段字典。

        Returns:
            bool: 更新成功返回 True。

        Raises:
            DatabaseError: record_id 为空或更新失败。
            RecordNotFoundError: 找不到指定记录。
        """
        if not record_id:
            raise DatabaseError("面试记录ID不能为空")

        self._ensure_tables_created()
        session = self.Session()
        try:
            record = session.query(TbInterviewRecordingAnalysis).filter(
                TbInterviewRecordingAnalysis.id == record_id
            ).first()

            if not record:
                raise RecordNotFoundError(int(record_id) if isinstance(record_id, (int, str)) and str(record_id).isdigit() else 0)

            for field, value in update_fields.items():
                if hasattr(record, field):
                    setattr(record, field, value)
                else:
                    print(f"警告: 字段 {field} 不存在于面试记录中，已跳过")

            session.commit()
            return True

        except (RecordNotFoundError, DatabaseError):
            # 已知异常直接抛出
            session.rollback()
            raise
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"更新面试记录失败: {str(exc)}")
        finally:
            session.close()

    def claim_next_interview_record(self) -> tuple[dict | None, bool]:
        """原子认领下一条待处理的面试记录。

        优先认领失败记录（FAILED），其次认领待处理记录（PENDING）。
        使用条件更新保证原子性，避免多 Worker 并发时重复处理同一条记录。
        如果候选记录被其他 Worker 抢占，会继续尝试下一条候选。

        Returns:
            tuple: (record_dict, from_failed)
                - record_dict: 认领成功的记录字典，如果没有可认领记录则为 None
                - from_failed: 是否从失败状态认领的（用于打印日志）

        Raises:
            DatabaseError: 数据库查询或更新失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            # 1. 优先尝试认领失败记录
            result = self._try_claim_by_status(session, expected_status=InterviewProcessingStatus.FAILED)
            if result is not None:
                record_dict, from_failed = result
                return record_dict, from_failed

            # 2. 如果没有失败记录或全部被抢占，尝试认领待处理记录
            result = self._try_claim_by_status(session, expected_status=InterviewProcessingStatus.PENDING)
            if result is not None:
                record_dict, from_failed = result
                return record_dict, from_failed

            # 3. 真的没有可认领任务
            return None, False

        except DatabaseError:
            # 已知异常直接抛出
            session.rollback()
            raise
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"认领面试记录失败: {str(exc)}")
        finally:
            session.close()

    def _try_claim_by_status(
        self, session, expected_status: int
    ) -> tuple[dict, bool] | None:
        """尝试认领指定状态的记录。

        Args:
            session: 数据库会话。
            expected_status: 期望的处理状态（InterviewProcessingStatus 枚举值）。

        Returns:
            tuple[dict, bool] | None: 认领成功返回 (record_dict, from_failed)，否则返回 None。

        Raises:
            DatabaseError: 数据库查询或更新失败时抛出。
        """
        from_failed = expected_status == InterviewProcessingStatus.FAILED
        excluded_ids: set[int] = set()

        while True:
            # 查询候选记录，排除已经尝试过的 ID
            query = (
                session.query(TbInterviewRecordingAnalysis)
                .filter(TbInterviewRecordingAnalysis.processing_status == expected_status)
                .order_by(TbInterviewRecordingAnalysis.update_time.asc())
            )

            if excluded_ids:
                query = query.filter(~TbInterviewRecordingAnalysis.id.in_(excluded_ids))

            candidate = query.first()

            if not candidate:
                return None

            # 使用条件更新进行原子认领
            result = session.query(TbInterviewRecordingAnalysis).filter(
                TbInterviewRecordingAnalysis.id == candidate.id,
                TbInterviewRecordingAnalysis.processing_status == expected_status,
            ).update({
                TbInterviewRecordingAnalysis.processing_status: InterviewProcessingStatus.PROCESSING,
                TbInterviewRecordingAnalysis.processing_tips: "正在处理中...",
            })

            session.commit()

            # 检查是否认领成功（affected rows == 1）
            if result == 1:
                # 认领成功，重新查询获取完整记录
                claimed_record = session.query(TbInterviewRecordingAnalysis).filter(
                    TbInterviewRecordingAnalysis.id == candidate.id
                ).first()

                if claimed_record:
                    record_dict = claimed_record.__dict__.copy()
                    record_dict.pop("_sa_instance_state", None)
                    return record_dict, from_failed

            # 记录被其他 Worker 抢占，排除该 ID 后继续尝试
            excluded_ids.add(candidate.id)

    def get_all_interview_records(
        self,
        filters: dict | None = None,
        exclude_fields: list[str] | None = None,
    ) -> list[dict]:
        """获取所有面试记录。

        Args:
            filters: 过滤条件字典。
            exclude_fields: 要排除的字段列表。

        Returns:
            list[dict]: 面试记录列表，如果没有数据返回空列表。

        Raises:
            DatabaseError: 查询失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            query = session.query(TbInterviewRecordingAnalysis)

            if filters:
                query = query.filter_by(**filters)

            if exclude_fields:
                all_columns = [column.name for column in TbInterviewRecordingAnalysis.__table__.columns]
                included_columns = [column for column in all_columns if column not in exclude_fields]
                query = query.with_entities(
                    *[getattr(TbInterviewRecordingAnalysis, col) for col in included_columns]
                )

            query = query.order_by(desc(TbInterviewRecordingAnalysis.update_time))
            records = query.all()

            if not records:
                return []

            records_dict = [
                record._asdict() if hasattr(record, "_asdict") else record.__dict__
                for record in records
            ]

            for record in records_dict:
                record.pop("_sa_instance_state", None)

            return records_dict

        except DatabaseError:
            # 已知异常直接抛出
            raise
        except Exception as exc:  # noqa: BLE001
            raise DatabaseError(f"查询面试记录失败: {str(exc)}")
        finally:
            session.close()

    def add_interview_analysis_detail(
        self,
        interview_record_analysis_id: int | str,
        interview_question: str | None = None,
        interviewee_answer: str | None = None,
        reference_answer: str | None = None,
        point_analysis: str | None = None,
        answer_thoughts: str | None = None,
        answer_evaluation: str | None = None,
        answer_score: float | None = None,
    ) -> int:
        """添加面试记录分析详情。

        Args:
            interview_record_analysis_id: 面试记录分析 ID。
            interview_question: 面试问题。
            interviewee_answer: 面试者回答。
            reference_answer: 参考答案。
            point_analysis: 考点分析。
            answer_thoughts: 答题思路。
            answer_evaluation: 回答评价。
            answer_score: 回答评分。

        Returns:
            int: 新详情记录的 ID。

        Raises:
            DatabaseError: interview_record_analysis_id 为空或添加失败时抛出。
        """
        if not interview_record_analysis_id:
            raise DatabaseError("面试记录分析ID不能为空")

        self._ensure_tables_created()
        session = self.Session()
        try:
            new_detail = TbInterviewRecordingAnalysisDetail(
                interview_record_analysis_id=interview_record_analysis_id,
                interview_question=interview_question,
                interviewee_answer=interviewee_answer,
                reference_answer=reference_answer,
                point_analysis=point_analysis,
                answer_thoughts=answer_thoughts,
                answer_evaluation=answer_evaluation,
                answer_score=answer_score,
            )

            session.add(new_detail)
            session.commit()

            return new_detail.id
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"添加面试记录分析详情失败: {str(exc)}")
        finally:
            session.close()

    def get_analysis_details_by_record_id(
        self, interview_record_analysis_id: int | str
    ) -> list[dict]:
        """根据面试记录分析 ID 查询分析详情。

        Args:
            interview_record_analysis_id: 面试记录分析 ID。

        Returns:
            list[dict]: 分析详情列表，如果没有明细返回空列表。

        Raises:
            DatabaseError: 查询失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            details = session.query(TbInterviewRecordingAnalysisDetail).filter(
                TbInterviewRecordingAnalysisDetail.interview_record_analysis_id
                == interview_record_analysis_id
            ).all()

            if not details:
                return []

            details_dict = [detail.__dict__ for detail in details]
            for detail in details_dict:
                detail.pop("_sa_instance_state", None)

            return details_dict
        except Exception as exc:  # noqa: BLE001
            raise DatabaseError(f"查询面试记录分析详情失败: {str(exc)}")
        finally:
            session.close()

    def delete_analysis_details_by_record_id(self, record_id: int | str) -> int:
        """删除指定面试记录的所有分析详情。

        Args:
            record_id: 面试记录 ID。

        Returns:
            int: 删除的记录条数。

        Raises:
            DatabaseError: record_id 为空或删除失败时抛出。
        """
        if not record_id:
            raise DatabaseError("面试记录分析ID不能为空")

        self._ensure_tables_created()
        session = self.Session()
        try:
            deleted_count = session.query(TbInterviewRecordingAnalysisDetail).filter(
                TbInterviewRecordingAnalysisDetail.interview_record_analysis_id == record_id
            ).delete()

            session.commit()

            return deleted_count
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"删除面试记录分析详情失败: {str(exc)}")
        finally:
            session.close()

    def get_asr_segment_cache(self, record_id: int | str) -> list[dict]:
        """获取指定记录的 ASR 分片缓存（按分片序号升序）。

        Args:
            record_id: 面试记录 ID。

        Returns:
            list[dict]: ASR 分片缓存列表，如果没有缓存返回空列表。

        Raises:
            DatabaseError: 查询失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            rows = (
                session.query(TbAsrSegmentCache)
                .filter(TbAsrSegmentCache.record_id == int(record_id))
                .order_by(TbAsrSegmentCache.segment_index.asc())
                .all()
            )
            result: list[dict] = []
            for row in rows:
                result.append(
                    {
                        "record_id": row.record_id,
                        "segment_index": row.segment_index,
                        "segment_path": row.segment_path,
                        "segment_text": row.segment_text,
                    }
                )
            return result
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DatabaseError(f"查询 ASR 分片缓存失败: {str(exc)}")
        finally:
            session.close()

    def upsert_asr_segment_cache(
        self,
        record_id: int | str,
        segment_index: int,
        segment_path: str,
        segment_text: str,
    ) -> bool:
        """写入或更新单个 ASR 分片缓存。

        Args:
            record_id: 面试记录 ID。
            segment_index: 分片序号。
            segment_path: 分片路径。
            segment_text: 分片文本。

        Returns:
            bool: 成功返回 True。

        Raises:
            DatabaseError: 写入失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            row = (
                session.query(TbAsrSegmentCache)
                .filter(
                    TbAsrSegmentCache.record_id == int(record_id),
                    TbAsrSegmentCache.segment_index == int(segment_index),
                )
                .first()
            )
            if row:
                row.segment_path = segment_path
                row.segment_text = segment_text
            else:
                row = TbAsrSegmentCache(
                    record_id=int(record_id),
                    segment_index=int(segment_index),
                    segment_path=segment_path,
                    segment_text=segment_text,
                )
                session.add(row)
            session.commit()
            return True
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"写入 ASR 分片缓存失败: {str(exc)}")
        finally:
            session.close()

    def clear_asr_segment_cache(self, record_id: int | str) -> int:
        """清空指定记录的 ASR 分片缓存。

        Args:
            record_id: 面试记录 ID。

        Returns:
            int: 删除的记录条数。

        Raises:
            DatabaseError: 清理失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            deleted_count = (
                session.query(TbAsrSegmentCache)
                .filter(TbAsrSegmentCache.record_id == int(record_id))
                .delete()
            )
            session.commit()
            return deleted_count
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"清理 ASR 分片缓存失败: {str(exc)}")
        finally:
            session.close()

    def get_extract_cache(self, record_id: int | str) -> list[dict] | None:
        """获取指定记录的 Q&A 抽取缓存。

        Args:
            record_id: 面试记录 ID。

        Returns:
            list[dict] | None: Q&A 列表，如果没有缓存返回 None。

        Raises:
            DatabaseError: 查询失败或缓存数据损坏时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            row = (
                session.query(TbInterviewExtractCache)
                .filter(TbInterviewExtractCache.record_id == int(record_id))
                .first()
            )
            if not row:
                return None

            try:
                data = json.loads(row.qa_json)
            except (json.JSONDecodeError, TypeError) as exc:
                raise DatabaseError(f"Q&A 抽取缓存数据损坏: {str(exc)}")

            if not isinstance(data, list):
                raise DatabaseError(
                    f"Q&A 抽取缓存数据格式错误: 期望 list，实际 {type(data).__name__}"
                )

            return data
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DatabaseError(f"查询 Q&A 抽取缓存失败: {str(exc)}")
        finally:
            session.close()

    def upsert_extract_cache(self, record_id: int | str, qa_list: list[dict]) -> bool:
        """写入或更新指定记录的 Q&A 抽取缓存。

        Args:
            record_id: 面试记录 ID。
            qa_list: Q&A 列表。

        Returns:
            bool: 成功返回 True。

        Raises:
            DatabaseError: 写入失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            payload = json.dumps(qa_list, ensure_ascii=False)
            row = (
                session.query(TbInterviewExtractCache)
                .filter(TbInterviewExtractCache.record_id == int(record_id))
                .first()
            )
            if row:
                row.qa_json = payload
            else:
                row = TbInterviewExtractCache(
                    record_id=int(record_id),
                    qa_json=payload,
                )
                session.add(row)
            session.commit()
            return True
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"写入 Q&A 抽取缓存失败: {str(exc)}")
        finally:
            session.close()

    def clear_extract_cache(self, record_id: int | str) -> int:
        """清空指定记录的 Q&A 抽取缓存。

        Args:
            record_id: 面试记录 ID。

        Returns:
            int: 删除的记录条数。

        Raises:
            DatabaseError: 清理失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            deleted_count = (
                session.query(TbInterviewExtractCache)
                .filter(TbInterviewExtractCache.record_id == int(record_id))
                .delete()
            )
            session.commit()
            return deleted_count
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"清理 Q&A 抽取缓存失败: {str(exc)}")
        finally:
            session.close()

    def get_analysis_cache(self, record_id: int | str) -> dict[int, dict]:
        """获取指定记录的逐题分析缓存，key 为 qa_index。

        Args:
            record_id: 面试记录 ID。

        Returns:
            dict[int, dict]: 逐题分析缓存字典，如果没有缓存返回空字典。

        Raises:
            DatabaseError: 查询失败或缓存数据损坏时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            rows = (
                session.query(TbInterviewAnalysisCache)
                .filter(TbInterviewAnalysisCache.record_id == int(record_id))
                .order_by(TbInterviewAnalysisCache.qa_index.asc())
                .all()
            )
            result: dict[int, dict] = {}
            for row in rows:
                try:
                    parsed = json.loads(row.qa_json)
                except (json.JSONDecodeError, TypeError) as exc:
                    raise DatabaseError(
                        f"逐题分析缓存数据损坏 (qa_index={row.qa_index}): {str(exc)}"
                    )

                if not isinstance(parsed, dict):
                    raise DatabaseError(
                        f"逐题分析缓存数据格式错误 (qa_index={row.qa_index}): "
                        f"期望 dict，实际 {type(parsed).__name__}"
                    )

                result[int(row.qa_index)] = parsed
            return result
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DatabaseError(f"查询逐题分析缓存失败: {str(exc)}")
        finally:
            session.close()

    def upsert_analysis_cache(
        self,
        record_id: int | str,
        qa_index: int,
        qa_item: dict,
    ) -> bool:
        """写入或更新指定记录的单题分析缓存。

        Args:
            record_id: 面试记录 ID。
            qa_index: 题目序号。
            qa_item: 题目分析数据。

        Returns:
            bool: 成功返回 True。

        Raises:
            DatabaseError: 写入失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            payload = json.dumps(qa_item, ensure_ascii=False)
            row = (
                session.query(TbInterviewAnalysisCache)
                .filter(
                    TbInterviewAnalysisCache.record_id == int(record_id),
                    TbInterviewAnalysisCache.qa_index == int(qa_index),
                )
                .first()
            )
            if row:
                row.qa_json = payload
            else:
                row = TbInterviewAnalysisCache(
                    record_id=int(record_id),
                    qa_index=int(qa_index),
                    qa_json=payload,
                )
                session.add(row)
            session.commit()
            return True
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"写入逐题分析缓存失败: {str(exc)}")
        finally:
            session.close()

    def clear_analysis_cache(self, record_id: int | str) -> int:
        """清空指定记录的逐题分析缓存。

        Args:
            record_id: 面试记录 ID。

        Returns:
            int: 删除的记录条数。

        Raises:
            DatabaseError: 清理失败时抛出。
        """
        self._ensure_tables_created()
        session = self.Session()
        try:
            deleted_count = (
                session.query(TbInterviewAnalysisCache)
                .filter(TbInterviewAnalysisCache.record_id == int(record_id))
                .delete()
            )
            session.commit()
            return deleted_count
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            raise DatabaseError(f"清理逐题分析缓存失败: {str(exc)}")
        finally:
            session.close()

def get_db_helper(
    host: str | None,
    user_name: str | None,
    password: str | None,
    db_name: str | None,
    port: int = 3306,
) -> DatabaseHelper:
    if not all([host, user_name, password, db_name]):
        raise ValueError(
            "数据库配置不完整，请检查 .env 文件中的 "
            "MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE_NAME"
        )
    database_url = f"mysql+pymysql://{user_name}:{password}@{host}:{port}/{db_name}"
    print(f"正在初始化数据库连接: {database_url}")
    return DatabaseHelper(database_url)


_my_db_helper: DatabaseHelper | None = None


def get_my_db_helper() -> DatabaseHelper:
    global _my_db_helper
    if _my_db_helper is None:
        conf: DbConfig = get_db_config()
        try:
            _my_db_helper = get_db_helper(
                conf.mysql_host,
                conf.mysql_user,
                conf.mysql_password,
                conf.mysql_database_name,
                conf.mysql_port,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"初始化数据库连接失败: {exc}")
            print("\n请检查以下配置：")
            print(f"  MYSQL_HOST: {conf.mysql_host}")
            print(f"  MYSQL_PORT: {conf.mysql_port}")
            print(f"  MYSQL_USER: {conf.mysql_user}")
            print(f"  MYSQL_DATABASE_NAME: {conf.mysql_database_name}")
            print("\n解决方案：")
            print("1. 确保 MySQL 服务已启动")
            print("2. 检查 .env 文件中的数据库配置是否正确")
            print("3. 确认数据库用户有足够的权限")
            raise
    return _my_db_helper


class _LazyDBHelper:
    """延迟加载的数据库助手包装器"""

    def __getattr__(self, name: str):
        return getattr(get_my_db_helper(), name)


my_db_helper = _LazyDBHelper()


