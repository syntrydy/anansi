"""Formatters for :mod:`anansi.experimental.stats_reporter` output."""

from __future__ import annotations

from anansi.experimental.stats_reporter import StatsReport


def format_stats(report: StatsReport) -> str:
    return (
        f"users={report.userCount} "
        f"jobs={report.job_count} "
        f"errors={report.ErrorCount}"
    )
