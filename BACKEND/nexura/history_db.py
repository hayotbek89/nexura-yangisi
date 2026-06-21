# Inspired by METATRON (MIT License) — github.com/sooryathejas/METATRON
# Adapted and integrated into NEXURA Scanner

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime

from nexura import config
from nexura.models.schemas import ScanReport

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = config.BASE_DIR / "nexura_history.db"


def _init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                target TEXT NOT NULL,
                intent TEXT,
                scan_date TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                tool_count INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                technologies TEXT
            );

            CREATE TABLE IF NOT EXISTS vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                name TEXT,
                severity TEXT,
                cve TEXT,
                cvss_score REAL,
                tool_source TEXT,
                url TEXT,
                description TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                port INTEGER,
                state TEXT,
                service TEXT,
                version TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                analysis_text TEXT,
                recommendations TEXT,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS verified_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                verification_token TEXT NOT NULL,
                verified BOOLEAN DEFAULT 0,
                verified_at TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_identifier TEXT,
                ip_address TEXT,
                target TEXT NOT NULL,
                action TEXT NOT NULL,
                tools_used TEXT,
                verification_status TEXT,
                tos_accepted BOOLEAN,
                result_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS tos_acceptance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_identifier TEXT NOT NULL UNIQUE,
                accepted_at TEXT NOT NULL,
                tos_version TEXT NOT NULL,
                ip_address TEXT
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                ai_backend TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, id);

            CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(scan_date);
            CREATE INDEX IF NOT EXISTS idx_vulns_session ON vulnerabilities(session_id);
            CREATE INDEX IF NOT EXISTS idx_ports_session ON ports(session_id);
        """)
        conn.commit()
    except Exception as e:
        logger.error("Database init error: %s", e)
    finally:
        conn.close()


class HistoryDB:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or str(DEFAULT_DB_PATH)
        self._local = threading.local()
        _init_db(self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn.isolation_level = None
        return self._local.conn

    def save_session(self, report: ScanReport, technologies: dict | None = None):
        conn = self._get_conn()
        try:
            conn.execute("BEGIN")

            duration = None
            if report.start_time and report.end_time:
                duration = int((report.end_time - report.start_time).total_seconds())

            conn.execute(
                """INSERT OR REPLACE INTO sessions
                   (id, target, intent, scan_date, status, tool_count, duration_seconds, technologies)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report.id,
                    report.target,
                    report.intent,
                    report.start_time.isoformat() if report.start_time else datetime.now().isoformat(),
                    report.status,
                    len(report.results),
                    duration,
                    json.dumps(technologies) if technologies else None,
                ),
            )

            conn.execute("DELETE FROM vulnerabilities WHERE session_id = ?", (report.id,))
            for result in report.results:
                for v in result.vulnerabilities:
                    conn.execute(
                        """INSERT INTO vulnerabilities
                           (session_id, name, severity, cve, cvss_score, tool_source, url, description)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            report.id,
                            v.name,
                            v.severity,
                            v.cve,
                            v.cvss,
                            result.tool,
                            v.url,
                            v.description,
                        ),
                    )

            conn.execute("DELETE FROM ports WHERE session_id = ?", (report.id,))
            for result in report.results:
                for p in result.ports:
                    conn.execute(
                        """INSERT INTO ports
                           (session_id, port, state, service, version)
                           VALUES (?, ?, ?, ?, ?)""",
                        (report.id, p.port, p.state, p.service, p.version),
                    )

            conn.execute("COMMIT")
            logger.info("Session %s saved to database", report.id)
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error("Failed to save session %s: %s", report.id, e)

    def get_all_sessions(self, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, target, intent, scan_date, status, tool_count, duration_seconds
                   FROM sessions ORDER BY scan_date DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            if not rows:
                return []

            ids = [r["id"] for r in rows]
            placeholders = ",".join("?" * len(ids))

            vuln_counts = {
                r["session_id"]: r["cnt"]
                for r in conn.execute(
                    f"SELECT session_id, COUNT(*) as cnt FROM vulnerabilities "
                    f"WHERE session_id IN ({placeholders}) GROUP BY session_id",
                    ids,
                ).fetchall()
            }
            severity_rows = conn.execute(
                f"""SELECT session_id, severity, COUNT(*) as cnt FROM vulnerabilities
                    WHERE session_id IN ({placeholders}) GROUP BY session_id, severity""",
                ids,
            ).fetchall()
            sev_map: dict[str, dict] = {}
            for sr in severity_rows:
                sid = sr["session_id"]
                if sid not in sev_map:
                    sev_map[sid] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
                sev = sr["severity"].upper()
                if sev in sev_map[sid]:
                    sev_map[sid][sev] = sr["cnt"]
            tool_rows = conn.execute(
                f"""SELECT session_id, tool_source FROM vulnerabilities
                    WHERE session_id IN ({placeholders}) AND tool_source IS NOT NULL
                    GROUP BY session_id, tool_source""",
                ids,
            ).fetchall()
            tools_map: dict[str, list[str]] = {}
            for tr in tool_rows:
                sid = tr["session_id"]
                tools_map.setdefault(sid, []).append(tr["tool_source"])

            result = []
            for row in rows:
                d = dict(row)
                d["total_vulns"] = vuln_counts.get(d["id"], 0)
                d["severities"] = sev_map.get(d["id"], {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0})
                d["tools"] = tools_map.get(d["id"], [])
                d["date"] = d.pop("scan_date")
                result.append(d)
            return result
        except Exception as e:
            logger.error("Failed to get sessions: %s", e)
            return []

    def get_session(self, session_id: str) -> dict | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, target, intent, scan_date, status, tool_count, "
                "duration_seconds, technologies FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return None
            session = dict(row)
            if session.get("technologies"):
                try:
                    session["technologies"] = json.loads(session["technologies"])
                except Exception:
                    session["technologies"] = {}
            session["vulnerabilities"] = [
                dict(r) for r in conn.execute(
                    "SELECT id, session_id, name, severity, cve, cvss_score, "
                    "tool_source, url, description FROM vulnerabilities WHERE session_id = ?",
                    (session_id,),
                ).fetchall()
            ]
            session["ports"] = [
                dict(r) for r in conn.execute(
                    "SELECT id, session_id, port, state, service, version "
                    "FROM ports WHERE session_id = ?",
                    (session_id,),
                ).fetchall()
            ]
            session["ai_analysis"] = [
                dict(r) for r in conn.execute(
                    "SELECT id, session_id, analysis_text, recommendations, created_at "
                    "FROM ai_analysis WHERE session_id = ?",
                    (session_id,),
                ).fetchall()
            ]
            return session
        except Exception as e:
            logger.error("Failed to get session %s: %s", session_id, e)
            return None

    def delete_session(self, session_id: str) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("BEGIN")
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.execute("COMMIT")
            return cursor.rowcount > 0
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error("Failed to delete session %s: %s", session_id, e)
            return False

    def save_ai_analysis(self, session_id: str, analysis_text: str, recommendations: list[str] | None = None):
        conn = self._get_conn()
        try:
            conn.execute("BEGIN")
            conn.execute(
                """INSERT INTO ai_analysis (session_id, analysis_text, recommendations, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    session_id,
                    analysis_text,
                    json.dumps(recommendations or []),
                    datetime.now().isoformat(),
                ),
            )
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error("Failed to save AI analysis: %s", e)

    # ---- Domain Verification ----

    def create_verification_request(self, domain: str, token: str) -> None:
        conn = self._get_conn()
        try:
            conn.execute("BEGIN")
            conn.execute(
                """INSERT OR REPLACE INTO verified_domains
                   (domain, verification_token, verified, created_at, expires_at)
                   VALUES (?, ?, 0, datetime('now'), datetime('now', '+24 hours'))""",
                (domain, token),
            )
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error("Failed to create verification request: %s", e)

    def mark_domain_verified(self, domain: str) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE verified_domains SET verified = 1, verified_at = datetime('now')
                   WHERE domain = ?""",
                (domain,),
            )
        except Exception as e:
            logger.error("Failed to mark domain verified: %s", e)

    def is_domain_verified(self, domain: str) -> bool:
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT verified FROM verified_domains
                   WHERE domain = ? AND expires_at > datetime('now')""",
                (domain,),
            ).fetchone()
            return row is not None and row["verified"] == 1
        except Exception as e:
            logger.error("Failed to check domain verification: %s", e)
            return False

    def get_verification_token(self, domain: str) -> str | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT verification_token FROM verified_domains WHERE domain = ?""",
                (domain,),
            ).fetchone()
            return row["verification_token"] if row else None
        except Exception as e:
            logger.error("Failed to get verification token: %s", e)
            return None

    # ---- Audit Log ----

    def log_audit_event(
        self,
        user_identifier: str | None,
        ip_address: str | None,
        target: str,
        action: str,
        tools_used: str | None = None,
        verification_status: str | None = None,
        tos_accepted: bool | None = None,
        result_summary: str | None = None,
    ) -> None:
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO audit_log
                   (timestamp, user_identifier, ip_address, target, action,
                    tools_used, verification_status, tos_accepted, result_summary)
                   VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_identifier, ip_address, target, action,
                 tools_used, verification_status, tos_accepted, result_summary),
            )
        except Exception as e:
            logger.error("Failed to log audit event: %s", e)

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM audit_log ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("Failed to get audit log: %s", e)
            return []

    # ---- ToS Acceptance ----

    def accept_tos(self, user_identifier: str, tos_version: str, ip_address: str | None = None) -> None:
        conn = self._get_conn()
        try:
            conn.execute("BEGIN")
            conn.execute(
                """INSERT OR REPLACE INTO tos_acceptance
                   (user_identifier, accepted_at, tos_version, ip_address)
                   VALUES (?, datetime('now'), ?, ?)""",
                (user_identifier, tos_version, ip_address),
            )
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.error("Failed to accept ToS: %s", e)

    def is_tos_accepted(self, user_identifier: str) -> bool:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM tos_acceptance WHERE user_identifier = ?",
                (user_identifier,),
            ).fetchone()
            return row is not None
        except Exception as e:
            logger.error("Failed to check ToS acceptance: %s", e)
            return False

    def save_chat_message(self, session_id: str, role: str, content: str, ai_backend: str | None = None):
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO chat_messages (session_id, role, content, ai_backend)
                   VALUES (?, ?, ?, ?)""",
                (session_id, role, content, ai_backend),
            )
        except Exception as e:
            logger.error("Failed to save chat message: %s", e)

    def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT role, content, ai_backend, created_at
                   FROM chat_messages
                   WHERE session_id = ?
                   ORDER BY id ASC
                   LIMIT ?""",
                (session_id, limit),
            ).fetchall()
            return [
                {
                    "role": r["role"],
                    "parts": [{"text": r["content"]}],
                    "ai_backend": r["ai_backend"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("Failed to get chat history: %s", e)
            return []

    def delete_chat_session(self, session_id: str) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            return True
        except Exception as e:
            logger.error("Failed to delete chat session: %s", e)
            return False

    def get_all_chat_sessions(self) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT session_id, COUNT(*) as msg_count,
                          MIN(created_at) as first_msg, MAX(created_at) as last_msg
                   FROM chat_messages
                   GROUP BY session_id
                   ORDER BY last_msg DESC
                   LIMIT 100"""
            ).fetchall()
            return [
                {
                    "session_id": r["session_id"],
                    "msg_count": r["msg_count"],
                    "first_msg": r["first_msg"],
                    "last_msg": r["last_msg"],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("Failed to get chat sessions: %s", e)
            return []

    def get_stats(self) -> dict:
        conn = self._get_conn()
        try:
            total_scans = conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()["cnt"]
            total_vulns = conn.execute("SELECT COUNT(*) as cnt FROM vulnerabilities").fetchone()["cnt"]
            critical = conn.execute(
                "SELECT COUNT(*) as cnt FROM vulnerabilities WHERE severity = 'CRITICAL'"
            ).fetchone()["cnt"]
            most_scanned = conn.execute(
                """SELECT target, COUNT(*) as cnt FROM sessions
                   GROUP BY target ORDER BY cnt DESC LIMIT 1"""
            ).fetchone()
            this_week = conn.execute(
                """SELECT COUNT(*) as cnt FROM sessions
                   WHERE scan_date >= datetime('now', '-7 days')"""
            ).fetchone()["cnt"]
            return {
                "total_scans": total_scans,
                "total_vulns": total_vulns,
                "critical_count": critical,
                "most_scanned_target": most_scanned["target"] if most_scanned else None,
                "this_week_scans": this_week,
            }
        except Exception as e:
            logger.error("Failed to get stats: %s", e)
            return {
                "total_scans": 0, "total_vulns": 0, "critical_count": 0,
                "most_scanned_target": None, "this_week_scans": 0,
            }
