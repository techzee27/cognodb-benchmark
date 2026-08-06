"""
Reads results/<platform>.json for every platform and emits:
  - docs/results_matrix.md  (markdown tables, paste straight into README)
  - docs/charts/*.png       (bar charts per metric, via matplotlib)

Run this after run_all.py has produced results for all platforms.

Usage:
    python -m harness.build_report
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = Path("results")
DOCS_DIR = Path("docs")
CHARTS_DIR = DOCS_DIR / "charts"

METRIC_ORDER = [
    "traversal_1hop", "traversal_2hop", "traversal_3hop",
    "point_lookup", "filtered_lookup", "aggregation_count",
]


def load_all_results() -> dict:
    data = {}
    for path in RESULTS_DIR.glob("*.json"):
        data[path.stem] = json.loads(path.read_text())
    return data


def build_latency_table(data: dict) -> str:
    lines = ["| Platform | Metric | p50 (ms) | p95 (ms) | n | failures |",
             "|---|---|---|---|---|---|"]
    for platform, metrics in sorted(data.items()):
        for metric_name in METRIC_ORDER:
            m = metrics.get(metric_name)
            if not m:
                continue
            lines.append(
                f"| {platform} | {metric_name} | {m['p50_ms']} | {m['p95_ms']} "
                f"| {m['n']} | {m['failures']} |"
            )
    return "\n".join(lines)


def build_mixed_table(data: dict) -> str:
    lines = ["| Platform | Concurrency | Throughput (ops/s) | Reads | Writes | Failures |",
             "|---|---|---|---|---|---|"]
    for platform, metrics in sorted(data.items()):
        mw = metrics.get("mixed_workload")
        if not mw:
            continue
        for level, res in sorted(mw["levels"].items()):
            lines.append(
                f"| {platform} | {res['concurrency']} | {res['throughput_ops_per_s']} "
                f"| {res['reads']} | {res['writes']} | {res['failures']} |"
            )
    return "\n".join(lines)


def build_charts(data: dict):
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for metric_name in METRIC_ORDER:
        platforms, p50s, p95s = [], [], []
        for platform, metrics in sorted(data.items()):
            m = metrics.get(metric_name)
            if not m:
                continue
            platforms.append(platform)
            p50s.append(m["p50_ms"])
            p95s.append(m["p95_ms"])
        if not platforms:
            continue

        x = range(len(platforms))
        width = 0.35
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar([i - width / 2 for i in x], p50s, width, label="p50")
        ax.bar([i + width / 2 for i in x], p95s, width, label="p95")
        ax.set_xticks(list(x))
        ax.set_xticklabels(platforms, rotation=20)
        ax.set_ylabel("Latency (ms)")
        ax.set_title(metric_name)
        ax.legend()
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / f"{metric_name}.png", dpi=120)
        plt.close(fig)


if __name__ == "__main__":
    data = load_all_results()
    if not data:
        print("No results found in results/. Run run_all.py first.")
        raise SystemExit(1)

    DOCS_DIR.mkdir(exist_ok=True)
    latency_md = build_latency_table(data)
    mixed_md = build_mixed_table(data)
    (DOCS_DIR / "results_matrix.md").write_text(
        f"## Latency results\n\n{latency_md}\n\n## Mixed workload results\n\n{mixed_md}\n"
    )
    build_charts(data)
    print(f"Wrote {DOCS_DIR / 'results_matrix.md'} and charts to {CHARTS_DIR}/")
