"""
ASR 分片断点缓存管理工具

查看 ASR 分片缓存状态、清理过期缓存（DB + 文件兜底）。

用法：
  python scripts/manage_asr_resume_cache.py status [--record-id ID]
  python scripts/manage_asr_resume_cache.py cleanup [--ttl-days N] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
refactor_root = Path(__file__).resolve().parents[1]
if str(refactor_root) not in sys.path:
    sys.path.insert(0, str(refactor_root))

from core.config import get_config
from core.utils.path_utils import get_file_path
from infra.db.db_helper import get_my_db_helper


def get_asr_resume_dir() -> Path:
    """获取 ASR 分片断点文件兜底目录。"""
    return Path(get_file_path("data/checkpoints/asr_resume")).resolve()


def get_asr_resume_files(record_id: int | None = None) -> list[Path]:
    """返回 ASR 兜底文件列表，仅包含当前目录下的普通 record_*.json 文件。"""
    asr_resume_dir = get_asr_resume_dir()
    if not asr_resume_dir.is_dir():
        return []

    pattern = f"record_{record_id}.json" if record_id is not None else "record_*.json"
    files: list[Path] = []
    for path in asr_resume_dir.glob(pattern):
        resolved_parent = path.parent.resolve()
        if (
            resolved_parent == asr_resume_dir
            and path.is_file()
            and not path.is_symlink()
        ):
            files.append(path)
    return sorted(files)


def show_status(record_id: int | None = None) -> None:
    """展示 ASR 分片缓存状态（DB + 文件兜底）"""
    print("=" * 80)
    print("ASR 分片断点缓存状态")
    print("=" * 80)

    # 1. DB 缓存状态
    print("\n[DB 缓存]")
    try:
        db_helper = get_my_db_helper()
        rows = db_helper.get_asr_segment_cache_status(record_id)
        if not rows:
            print("  暂无 ASR 分片缓存记录")
        else:
            print(f"  共 {len(rows)} 条记录:")
            print(f"  {'record_id':<12} {'分片数':<8} {'最早更新时间':<22} {'最新更新时间':<22}")
            print(f"  {'-'*12} {'-'*8} {'-'*22} {'-'*22}")
            for row in rows:
                first_t = row["first_update_time"] or "N/A"
                last_t = row["last_update_time"] or "N/A"
                print(
                    f"  {row['record_id']:<12} {row['segment_count']:<8} "
                    f"{str(first_t):<22} {str(last_t):<22}"
                )
    except Exception as exc:
        print(f"  ❌ 查询 DB 缓存失败: {exc}")

    # 2. 文件兜底状态
    print("\n[文件兜底缓存]")
    asr_resume_dir = get_asr_resume_dir()
    if not asr_resume_dir.is_dir():
        print(f"  目录不存在: {asr_resume_dir}")
    else:
        files = get_asr_resume_files(record_id)
        if not files:
            print(f"  目录: {asr_resume_dir}")
            print("  暂无兜底文件")
        else:
            print(f"  目录: {asr_resume_dir}")
            print(f"  共 {len(files)} 个兜底文件:")
            for fp in files:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                size_kb = fp.stat().st_size / 1024
                print(f"    {fp.name:<40} 修改时间: {mtime}  大小: {size_kb:.1f} KB")

    print("\n" + "=" * 80)


def run_cleanup(ttl_days: int | None = None, dry_run: bool = False) -> None:
    """清理过期 ASR 分片缓存（DB + 文件兜底）"""
    if ttl_days is None:
        ttl_days = get_config().asr_resume_cache_ttl_days
    if ttl_days < 0:
        raise ValueError("ttl-days 不能小于 0")

    cutoff_time = datetime.now() - timedelta(days=ttl_days)

    print("=" * 80)
    print("ASR 分片断点缓存清理")
    print("=" * 80)
    print(f"\nTTL: {ttl_days} 天")
    print(f"截止时间: {cutoff_time}")
    if dry_run:
        print("模式: dry-run（仅预览，不实际删除）")
    else:
        print("模式: 实际清理")

    total_deleted = 0

    # 1. DB 缓存清理
    print("\n[DB 缓存清理]")
    try:
        db_helper = get_my_db_helper()
        if dry_run:
            candidates = db_helper.get_expired_asr_segment_cache_status(cutoff_time)
            if candidates:
                print(f"  将删除以下 {len(candidates)} 条记录中的过期分片:")
                for r in candidates:
                    print(
                        f"    record_id={r['record_id']}  "
                        f"过期分片数={r['expired_segment_count']}  "
                        f"最早更新={r['first_update_time']}  "
                        f"最晚过期更新={r['last_update_time']}"
                    )
            else:
                print("  无过期 DB 缓存需要清理")
        else:
            deleted = db_helper.clear_expired_asr_segment_cache(cutoff_time)
            total_deleted += deleted
            if deleted > 0:
                print(f"  ✅ 已删除 {deleted} 条过期 DB 缓存记录")
            else:
                print("  ✓ 无过期 DB 缓存需要清理")
    except Exception as exc:
        print(f"  ❌ DB 缓存清理失败: {exc}")

    # 2. 文件兜底清理
    print("\n[文件兜底清理]")
    asr_resume_dir = get_asr_resume_dir()
    if not asr_resume_dir.is_dir():
        print(f"  目录不存在: {asr_resume_dir}")
    else:
        files = get_asr_resume_files()
        expired_files = [
            fp for fp in files
            if datetime.fromtimestamp(fp.stat().st_mtime) < cutoff_time
        ]

        if not expired_files:
            print("  ✓ 无过期兜底文件需要清理")
        elif dry_run:
            print(f"  将删除以下 {len(expired_files)} 个文件:")
            for fp in expired_files:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                print(f"    {fp.name}  修改时间: {mtime}")
        else:
            deleted_files = 0
            for fp in expired_files:
                try:
                    fp.unlink()
                    print(f"    ✅ 已删除: {fp.name}")
                    deleted_files += 1
                except OSError as exc:
                    print(f"    ❌ 删除失败 {fp.name}: {exc}")
            total_deleted += deleted_files
            print(f"  共删除 {deleted_files} 个过期兜底文件")

    print(f"\n清理完成。总删除条目: {total_deleted}")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ASR 分片断点缓存管理工具"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status 子命令
    status_parser = subparsers.add_parser("status", help="查看 ASR 分片缓存状态")
    status_parser.add_argument(
        "--record-id", type=int, default=None, help="指定记录 ID（不指定则查询全部）"
    )

    # cleanup 子命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理过期 ASR 分片缓存")
    cleanup_parser.add_argument(
        "--ttl-days", type=int, default=None,
        help="缓存保留天数（默认读取 ASR_RESUME_CACHE_TTL_DAYS 配置）"
    )
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help="仅预览，不实际删除"
    )

    args = parser.parse_args()

    if args.command == "status":
        show_status(record_id=args.record_id)
    elif args.command == "cleanup":
        run_cleanup(ttl_days=args.ttl_days, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
