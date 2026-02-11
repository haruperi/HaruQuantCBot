"""
Validation report generation for HQT Trading System.

This module provides the ValidationReport class that summarizes
validation results and exports to multiple formats.

[REQ: DAT-FR-014] Validation report with multiple export formats.
"""

from collections import Counter
from typing import Any

import pandas as pd

from hqt.data.validation.models import IssueSeverity, IssueType, ValidationIssue


class ValidationReport:
    """
    Comprehensive validation report with multiple export formats.

    The report summarizes all detected issues with counts, severities,
    and affected timestamps. Supports export to dict, DataFrame, and HTML.

    Attributes:
        symbol: Trading symbol that was validated
        issues: List of all detected ValidationIssue objects
        total_bars: Total number of bars validated
        checks_run: List of check names that were executed

    Example:
        ```python
        # Create report
        report = ValidationReport(
            symbol="EURUSD",
            issues=detected_issues,
            total_bars=1000,
            checks_run=["PriceSanityCheck", "GapDetector"],
        )

        # Get summary
        print(f"Total issues: {report.total_issues}")
        print(f"Pass rate: {report.pass_rate:.1%}")

        # Export to different formats
        data_dict = report.to_dict()
        df = report.to_dataframe()
        html = report.to_html()
        ```
    """

    def __init__(
        self,
        symbol: str,
        issues: list[ValidationIssue],
        total_bars: int,
        checks_run: list[str],
    ):
        """
        Initialize validation report.

        Args:
            symbol: Trading symbol
            issues: List of detected issues
            total_bars: Total number of bars validated
            checks_run: List of check names executed
        """
        self.symbol = symbol
        self.issues = issues
        self.total_bars = total_bars
        self.checks_run = checks_run

    @property
    def total_issues(self) -> int:
        """Total number of issues detected."""
        return len(self.issues)

    @property
    def clean(self) -> bool:
        """Whether the data is clean (no issues)."""
        return len(self.issues) == 0

    @property
    def pass_rate(self) -> float:
        """Percentage of bars without issues (0.0 to 1.0)."""
        if self.total_bars == 0:
            return 1.0
        affected_bars = len(set(issue.timestamp for issue in self.issues))
        return (self.total_bars - affected_bars) / self.total_bars

    @property
    def severity_counts(self) -> dict[str, int]:
        """Count of issues by severity level."""
        counter = Counter(issue.severity.value for issue in self.issues)
        return {
            "INFO": counter.get("INFO", 0),
            "WARNING": counter.get("WARNING", 0),
            "ERROR": counter.get("ERROR", 0),
            "CRITICAL": counter.get("CRITICAL", 0),
        }

    @property
    def type_counts(self) -> dict[str, int]:
        """Count of issues by type."""
        counter = Counter(issue.issue_type.value for issue in self.issues)
        return dict(counter)

    @property
    def check_counts(self) -> dict[str, int]:
        """Count of issues by check name."""
        counter = Counter(issue.check_name for issue in self.issues)
        return dict(counter)

    @property
    def critical_count(self) -> int:
        """Number of critical issues."""
        return self.severity_counts["CRITICAL"]

    @property
    def error_count(self) -> int:
        """Number of error issues."""
        return self.severity_counts["ERROR"]

    @property
    def warning_count(self) -> int:
        """Number of warning issues."""
        return self.severity_counts["WARNING"]

    @property
    def info_count(self) -> int:
        """Number of info issues."""
        return self.severity_counts["INFO"]

    def get_issues_by_severity(self, severity: IssueSeverity) -> list[ValidationIssue]:
        """
        Get all issues of a specific severity level.

        Args:
            severity: Severity level to filter by

        Returns:
            List of issues with the specified severity
        """
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_type(self, issue_type: IssueType) -> list[ValidationIssue]:
        """
        Get all issues of a specific type.

        Args:
            issue_type: Issue type to filter by

        Returns:
            List of issues with the specified type
        """
        return [issue for issue in self.issues if issue.issue_type == issue_type]

    def to_dict(self) -> dict[str, Any]:
        """
        Export report to dictionary.

        Returns:
            Dictionary with complete report data

        Example:
            ```python
            report_dict = report.to_dict()
            print(report_dict["summary"]["total_issues"])
            ```
        """
        return {
            "symbol": self.symbol,
            "summary": {
                "total_bars": self.total_bars,
                "total_issues": self.total_issues,
                "clean": self.clean,
                "pass_rate": self.pass_rate,
                "checks_run": self.checks_run,
            },
            "severity_breakdown": self.severity_counts,
            "type_breakdown": self.type_counts,
            "check_breakdown": self.check_counts,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_dataframe(self) -> pd.DataFrame:
        """
        Export issues to pandas DataFrame.

        Returns:
            DataFrame with one row per issue

        Example:
            ```python
            df = report.to_dataframe()
            print(df.groupby("severity").size())
            ```
        """
        if not self.issues:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "issue_type",
                    "severity",
                    "check_name",
                    "message",
                    "details",
                ]
            )

        records = []
        for issue in self.issues:
            records.append(
                {
                    "timestamp": issue.timestamp,
                    "datetime": issue.datetime,
                    "issue_type": issue.issue_type.value,
                    "severity": issue.severity.value,
                    "check_name": issue.check_name,
                    "message": issue.message,
                    "details": str(issue.details),
                }
            )

        df = pd.DataFrame(records)
        df = df.sort_values("timestamp")
        return df

    def to_html(self, include_details: bool = True) -> str:
        """
        Export report to HTML format.

        Args:
            include_details: Whether to include full issue details table

        Returns:
            HTML string with formatted report

        Example:
            ```python
            html = report.to_html()
            with open("report.html", "w") as f:
                f.write(html)
            ```
        """
        severity_colors = {
            "INFO": "#17a2b8",
            "WARNING": "#ffc107",
            "ERROR": "#fd7e14",
            "CRITICAL": "#dc3545",
        }

        html_parts = []

        # Header
        html_parts.append("<html><head><style>")
        html_parts.append(
            """
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            h2 { color: #666; margin-top: 30px; }
            .summary { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .metric { display: inline-block; margin: 10px 20px 10px 0; }
            .metric-label { font-weight: bold; color: #666; }
            .metric-value { font-size: 24px; font-weight: bold; color: #333; }
            .badge { padding: 5px 10px; border-radius: 3px; color: white; font-weight: bold; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th { background: #333; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #ddd; }
            tr:hover { background: #f5f5f5; }
            .status-clean { color: #28a745; font-weight: bold; }
            .status-issues { color: #dc3545; font-weight: bold; }
            """
        )
        html_parts.append("</style></head><body>")

        # Title
        html_parts.append(f"<h1>Validation Report: {self.symbol}</h1>")

        # Summary section
        html_parts.append('<div class="summary">')
        html_parts.append(f'<div class="metric">')
        html_parts.append(f'<div class="metric-label">Total Bars</div>')
        html_parts.append(f'<div class="metric-value">{self.total_bars:,}</div>')
        html_parts.append(f"</div>")

        html_parts.append(f'<div class="metric">')
        html_parts.append(f'<div class="metric-label">Total Issues</div>')
        html_parts.append(f'<div class="metric-value">{self.total_issues:,}</div>')
        html_parts.append(f"</div>")

        html_parts.append(f'<div class="metric">')
        html_parts.append(f'<div class="metric-label">Pass Rate</div>')
        html_parts.append(f'<div class="metric-value">{self.pass_rate:.1%}</div>')
        html_parts.append(f"</div>")

        html_parts.append(f'<div class="metric">')
        html_parts.append(f'<div class="metric-label">Status</div>')
        status_class = "status-clean" if self.clean else "status-issues"
        status_text = "CLEAN" if self.clean else "ISSUES DETECTED"
        html_parts.append(f'<div class="metric-value {status_class}">{status_text}</div>')
        html_parts.append(f"</div>")
        html_parts.append("</div>")

        # Severity breakdown
        html_parts.append("<h2>Severity Breakdown</h2>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Severity</th><th>Count</th></tr>")
        for severity, count in self.severity_counts.items():
            color = severity_colors.get(severity, "#999")
            html_parts.append(f"<tr>")
            html_parts.append(
                f'<td><span class="badge" style="background:{color}">{severity}</span></td>'
            )
            html_parts.append(f"<td>{count:,}</td>")
            html_parts.append(f"</tr>")
        html_parts.append("</table>")

        # Type breakdown
        html_parts.append("<h2>Issue Type Breakdown</h2>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Type</th><th>Count</th></tr>")
        for issue_type, count in sorted(self.type_counts.items(), key=lambda x: -x[1]):
            html_parts.append(f"<tr><td>{issue_type}</td><td>{count:,}</td></tr>")
        html_parts.append("</table>")

        # Check breakdown
        html_parts.append("<h2>Check Breakdown</h2>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Check</th><th>Issues Found</th></tr>")
        for check, count in sorted(self.check_counts.items(), key=lambda x: -x[1]):
            html_parts.append(f"<tr><td>{check}</td><td>{count:,}</td></tr>")
        html_parts.append("</table>")

        # Detailed issues table
        if include_details and self.issues:
            html_parts.append("<h2>Detailed Issues</h2>")
            df = self.to_dataframe()
            html_parts.append(df.to_html(index=False, escape=False))

        # Footer
        html_parts.append("</body></html>")

        return "\n".join(html_parts)

    def __repr__(self) -> str:
        """Return string representation of the report."""
        return (
            f"ValidationReport(symbol={self.symbol!r}, "
            f"total_issues={self.total_issues}, "
            f"pass_rate={self.pass_rate:.1%})"
        )

    def __str__(self) -> str:
        """Return human-readable string representation."""
        lines = [
            f"Validation Report: {self.symbol}",
            f"{'=' * 50}",
            f"Total Bars: {self.total_bars:,}",
            f"Total Issues: {self.total_issues:,}",
            f"Pass Rate: {self.pass_rate:.1%}",
            f"Status: {'CLEAN' if self.clean else 'ISSUES DETECTED'}",
            "",
            "Severity Breakdown:",
        ]

        for severity, count in self.severity_counts.items():
            if count > 0:
                lines.append(f"  {severity}: {count:,}")

        if self.type_counts:
            lines.append("")
            lines.append("Issue Types:")
            for issue_type, count in sorted(
                self.type_counts.items(), key=lambda x: -x[1]
            ):
                lines.append(f"  {issue_type}: {count:,}")

        return "\n".join(lines)
