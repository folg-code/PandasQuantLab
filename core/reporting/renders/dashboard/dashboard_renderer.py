from pathlib import Path
import json
import shutil
from jinja2 import Environment, FileSystemLoader


class DashboardRenderer:
    """
    Renders RiskReport into HTML dashboard.
    NO computations.
    """

    def __init__(self, run_path: Path):
        base = Path(__file__).parent
        self.template_dir = base / "templates"
        self.static_dir = base / "static"

        self.output_dir = run_path / "report"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
        )

    def render(self, report_data: dict, ctx) -> Path:
        template = self.env.get_template("dashboard.html")

        html = template.render(
            report=report_data,
            report_json=json.dumps(
                {
                    **report_data,
                    "__equity__": {
                        "time": ctx.trades["exit_time"].astype(str).tolist(),
                        "equity": ctx.trades["equity"].tolist(),
                        "drawdown": ctx.trades["drawdown"].tolist(),
                    },
                },
                default=str,
            ),
        )

        out = self.output_dir / "dashboard.html"
        out.write_text(html, encoding="utf-8")

        self._copy_static()
        return out

    def _copy_static(self):
        target = self.output_dir / "static"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.static_dir, target)

