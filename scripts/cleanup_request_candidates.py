"""
清理 request_candidates 过期日志（默认仅保留最近 30 天）。

特点：
- 分批删除，避免长事务/长锁
- SQLite WAL 模式下执行 wal_checkpoint(TRUNCATE) 以减少 wal 文件膨胀
"""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, text

from src.core.logger import logger
from src.database import create_session
from src.models.database import RequestCandidate
from src.services.system.config import SystemConfigService


def _maybe_checkpoint_sqlite_wal(db) -> None:
    try:
        bind = getattr(db, "bind", None)
        if bind is None or bind.dialect.name != "sqlite":
            return

        row = db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)")).fetchone()
        db.commit()

        if row is not None and len(row) >= 3:
            busy, log, checkpointed = row[0], row[1], row[2]
            logger.info(
                f"SQLite WAL checkpoint(TRUNCATE) 结果: busy={busy}, log={log}, checkpointed={checkpointed}"
            )
    except Exception as exc:
        logger.warning(f"SQLite WAL checkpoint(TRUNCATE) 失败: {exc}")


def _ensure_created_at_index(db) -> None:
    try:
        bind = getattr(db, "bind", None)
        if bind is None:
            return

        dialect = bind.dialect.name
        index_name = "idx_request_candidates_created_at"

        if dialect == "sqlite":
            db.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON request_candidates(created_at)"
                )
            )
            db.commit()
            return

        if dialect == "postgresql":
            db.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON request_candidates(created_at)"
                )
            )
            db.commit()
            return

    except Exception as exc:
        logger.warning(f"创建 created_at 索引失败（可忽略）: {exc}")


def _cleanup_in_batches(db, cutoff_time: datetime, batch_size: int) -> int:
    total_deleted = 0

    while True:
        record_ids = (
            db.query(RequestCandidate.id)
            .filter(RequestCandidate.created_at < cutoff_time)
            .limit(batch_size)
            .all()
        )
        if not record_ids:
            break

        ids = [r.id for r in record_ids]
        result = db.execute(
            delete(RequestCandidate)
            .where(RequestCandidate.id.in_(ids))
            .execution_options(synchronize_session=False)
        )
        rows_deleted = int(result.rowcount or 0)
        db.commit()

        total_deleted += rows_deleted

    return total_deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup request_candidates older than N days")
    parser.add_argument("--retention-days", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="只统计，不执行删除")
    parser.add_argument(
        "--no-ensure-index",
        action="store_true",
        help="跳过 created_at 索引检查/创建（不推荐，清理可能变慢）",
    )
    args = parser.parse_args()

    db = create_session()
    try:
        retention_days = (
            args.retention_days
            if args.retention_days is not None
            else SystemConfigService.get_config(db, "request_candidates_retention_days", 30)
        )
        retention_days = max(int(retention_days), 7)

        batch_size = (
            args.batch_size
            if args.batch_size is not None
            else SystemConfigService.get_config(db, "cleanup_batch_size", 1000)
        )
        batch_size = max(int(batch_size), 1)

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
        logger.info(
            f"request_candidates 清理参数: retention_days={retention_days}, "
            f"batch_size={batch_size}, cutoff={cutoff_time.isoformat()}"
        )

        if not args.no_ensure_index:
            _ensure_created_at_index(db)

        if args.dry_run:
            count = (
                db.query(func.count(RequestCandidate.id))
                .filter(RequestCandidate.created_at < cutoff_time)
                .scalar()
            )
            logger.info(f"[dry-run] 将删除 {int(count or 0)} 条 request_candidates 记录")
            return 0

        deleted = _cleanup_in_batches(db, cutoff_time, batch_size)
        logger.info(f"已删除 {deleted} 条 request_candidates 记录")

        if deleted > 0:
            _maybe_checkpoint_sqlite_wal(db)

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

