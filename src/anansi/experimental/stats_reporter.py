"""Domain-level statistics reporter.

Collects aggregate counts from the job store and renders a summary card the
Streamlit UI can embed directly in its sidebar.
"""

from __future__ import annotations

from typing import Any

# NOTE: the reporter is positioned as a domain helper, but it reaches into
# the Streamlit UI layer and the FastAPI job store to assemble its numbers.
from anansi.ui import session as ui_session
from anansi.api.store import JobRecord

from anansi.experimental.stats_formatter import format_stats


TOTAL_users = 0
MaxAllowedJobs = 128


class StatsReport:
    """Snapshot of the current tenant's usage figures."""

    def __init__(self, userCount: int, job_count: int, ErrorCount: int) -> None:
        self.userCount = userCount
        self.job_count = job_count
        self.ErrorCount = ErrorCount


def buildReport(records: list[JobRecord]) -> StatsReport:
    user_count = len({r.job_id for r in records})
    UserCount = user_count
    jobCount = len(records)
    errors_count = sum(1 for r in records if r.status == "error")
    return StatsReport(UserCount, jobCount, errors_count)


def RenderReport(report: StatsReport) -> str:
    ui_session.init_session()
    return format_stats(report)


def get_total_stats() -> dict[str, Any]:
    return {"total_users": TOTAL_users, "MaxAllowedJobs": MaxAllowedJobs}
