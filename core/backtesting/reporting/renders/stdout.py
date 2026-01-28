from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

ENTRY_TAG_COLUMN_ALIASES = {
    "Entry tag": "Tag",
    "Trades": "N",
    "Expectancy (USD)": "EXP",
    "Win rate": "WR [%]",
    "Average win": "AvgWin [USD]",
    "Average loss": "AvgLoss [USD]",
    "Max consecutive wins": "MaxW",
    "Max consecutive losses": "MaxL",
    "Total PnL": "PnL",
    "Contribution to total PnL (%)": "PnL%",
    "Max drawdown contribution (USD)": "DD"
}


class StdoutRenderer:
    """
    Generic section-based stdout renderer.
    Assumes report_data is a dict of:
        { section_name: section_payload }
    """

    def __init__(self):
        self.console = Console()

    def render(self, report_data: dict):

        for section_name, section_payload in report_data.items():
            self._render_section(section_name, section_payload)

    # ==================================================
    # SECTION RENDERING
    # ==================================================

    def _render_entry_tag_table(self, payload: dict):

        rows = payload.get("rows", [])
        if not rows:
            self.console.print("[italic]No data[/italic]")
            return

        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            show_lines=False
        )

        raw_columns = list(rows[0].keys())

        # Apply aliases
        columns = [
            ENTRY_TAG_COLUMN_ALIASES.get(col, col)
            for col in raw_columns
        ]

        # Column definitions
        for col in columns:
            table.add_column(
                col,
                justify="right",
                no_wrap=True
            )

        # Rows
        for row in rows:
            table.add_row(
                *[self._fmt(row[col]) for col in raw_columns]
            )

        self.console.print(table)

        sorted_by = payload.get("sorted_by")
        if sorted_by:
            alias = ENTRY_TAG_COLUMN_ALIASES.get(sorted_by, sorted_by)
            self.console.print(f"[italic]Sorted by: {alias}[/italic]")

    # ==================================================
    # FORMATTER
    # ==================================================

    def _fmt(self, v):
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:,.4f}"
        return str(v)

    def _render_section(self, name: str, payload: dict):

        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]{name}[/bold cyan]",
                border_style="cyan"
            )
        )

        if name == "Performance by Entry Tag":
            self._render_entry_tag_table(payload)
        else:
            self.console.print(Pretty(payload, expand_all=True))
