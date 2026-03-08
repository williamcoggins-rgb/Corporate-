"""Base agent class — all bots inherit from this.

Every agent logs its run to the agent_runs table so you always know
what ran, when, and what it touched.
"""

import datetime
from warehouse.db import get_connection


class BaseAgent:
    """Base class for all competitive intelligence agents."""

    name = "base_agent"
    description = "Base agent — override in subclass"
    tier = 0  # 1=Scout, 2=Transform, 3=Analytics, 4=Alert

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.run_id = None
        self.records_processed = 0
        self._log_lines = []

    def log(self, msg):
        """Log a message (printed + stored)."""
        line = f"[{self.name}] {msg}"
        print(line)
        self._log_lines.append(line)

    def _start_run(self):
        con = get_connection()
        self.run_id = con.execute("SELECT nextval('seq_agent_run')").fetchone()[0]
        con.execute(
            "INSERT INTO agent_runs (run_id, agent_name) VALUES (?, ?)",
            [self.run_id, self.name],
        )
        con.close()
        self.log(f"Run #{self.run_id} started")

    def _finish_run(self, status="completed", notes=None):
        con = get_connection()
        con.execute(
            """UPDATE agent_runs
               SET finished_at = CURRENT_TIMESTAMP,
                   status = ?,
                   records_processed = ?,
                   notes = ?
               WHERE run_id = ?""",
            [status, self.records_processed, notes or "\n".join(self._log_lines[-10:]), self.run_id],
        )
        con.close()
        self.log(f"Run #{self.run_id} {status} — {self.records_processed} records processed")

    def execute(self):
        """Override this with the agent's actual work."""
        raise NotImplementedError("Subclass must implement execute()")

    def run(self):
        """Full lifecycle: start → execute → finish."""
        self._start_run()
        try:
            self.execute()
            self._finish_run("completed")
        except Exception as e:
            self.log(f"ERROR: {e}")
            self._finish_run("failed", str(e))
            raise

    def create_alert(self, alert_type, title, detail=None, severity="info",
                     competitor_id=None, data_json=None):
        """Write an alert to the alerts_log table."""
        con = get_connection()
        aid = con.execute("SELECT nextval('seq_alert')").fetchone()[0]
        con.execute(
            """INSERT INTO alerts_log
               (alert_id, alert_type, severity, competitor_id, title, detail, data_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [aid, alert_type, severity, competitor_id, title, detail, data_json],
        )
        con.close()
        self.log(f"ALERT [{severity}]: {title}")
        return aid
