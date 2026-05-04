"""ATM IV history + rank/percentile, persisted in SQLite.

Rank   = (current - min) / (max - min) * 100 over trailing window
Percentile = % of historical samples below current
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class IVHistoryStore:
    def __init__(self, db_path: str | Path = "iv_history.sqlite") -> None:
        self.db_path = Path(db_path)
        self._init()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS iv_snapshots (
                    symbol TEXT NOT NULL,
                    snapshot_at TEXT NOT NULL,
                    atm_iv REAL NOT NULL,
                    PRIMARY KEY (symbol, snapshot_at)
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS ix_iv_symbol ON iv_snapshots(symbol)")

    def record(self, symbol: str, atm_iv: float, when: Optional[datetime] = None) -> None:
        when = when or datetime.utcnow()
        # De-dupe: collapse to one snapshot per symbol per hour to avoid
        # spamming the DB on every chain refresh.
        bucket = when.replace(minute=0, second=0, microsecond=0).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO iv_snapshots (symbol, snapshot_at, atm_iv) VALUES (?, ?, ?)",
                (symbol.upper(), bucket, float(atm_iv)),
            )

    def history(self, symbol: str, lookback_days: int = 252) -> list[tuple[datetime, float]]:
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        with self._conn() as c:
            rows = c.execute(
                "SELECT snapshot_at, atm_iv FROM iv_snapshots "
                "WHERE symbol = ? AND snapshot_at >= ? ORDER BY snapshot_at ASC",
                (symbol.upper(), cutoff),
            ).fetchall()
        return [(datetime.fromisoformat(t), iv) for t, iv in rows]

    def rank(self, symbol: str, current_iv: float, lookback_days: int = 252) -> Optional[dict]:
        hist = self.history(symbol, lookback_days)
        if len(hist) < 5:
            return None
        ivs = [iv for _, iv in hist]
        lo, hi = min(ivs), max(ivs)
        below = sum(1 for v in ivs if v < current_iv)
        rank_pct = 100 * (current_iv - lo) / (hi - lo) if hi > lo else 50.0
        percentile = 100 * below / len(ivs)
        return {
            "current_iv": current_iv,
            "rank": max(0.0, min(100.0, rank_pct)),
            "percentile": percentile,
            "min_iv": lo,
            "max_iv": hi,
            "samples": len(ivs),
            "lookback_days": lookback_days,
        }
