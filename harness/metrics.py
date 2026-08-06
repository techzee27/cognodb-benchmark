"""
Shared timing + percentile utilities. Every workload runner should use
Timer to collect a list of per-query latencies (in ms), then summarize()
to get p50/p95/mean/etc for the results table.
"""

import time
import json
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Any


class Timer:
    """Context manager that records elapsed wall-clock time in milliseconds."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


@dataclass
class LatencyStats:
    n: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    failures: int = 0


def summarize(latencies_ms: list[float], failures: int = 0) -> LatencyStats:
    if not latencies_ms:
        return LatencyStats(0, 0, 0, 0, 0, 0, 0, failures)
    sorted_lat = sorted(latencies_ms)
    return LatencyStats(
        n=len(sorted_lat),
        p50_ms=round(statistics.median(sorted_lat), 3),
        p95_ms=round(_percentile(sorted_lat, 95), 3),
        p99_ms=round(_percentile(sorted_lat, 99), 3),
        mean_ms=round(statistics.mean(sorted_lat), 3),
        min_ms=round(sorted_lat[0], 3),
        max_ms=round(sorted_lat[-1], 3),
        failures=failures,
    )


def _percentile(sorted_data: list[float], pct: float) -> float:
    if len(sorted_data) == 1:
        return sorted_data[0]
    k = (len(sorted_data) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def run_warmed_up(
    fn: Callable[[], Any],
    iterations: int = 100,
    warmup: int = 10,
) -> LatencyStats:
    """Run fn() `warmup` times (discarded), then `iterations` times, timing each."""
    failures = 0
    for _ in range(warmup):
        try:
            fn()
        except Exception:
            pass  # warmup failures don't count

    latencies = []
    for _ in range(iterations):
        try:
            with Timer() as t:
                fn()
            latencies.append(t.elapsed_ms)
        except Exception:
            failures += 1
    return summarize(latencies, failures)


def save_result(platform: str, workload: str, stats: LatencyStats, outdir: str = "results", extra: dict = None):
    """Append a result record to results/<platform>.json"""
    Path(outdir).mkdir(exist_ok=True)
    path = Path(outdir) / f"{platform}.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    record = asdict(stats)
    if extra:
        record.update(extra)
    data[workload] = record
    path.write_text(json.dumps(data, indent=2))
    print(f"[{platform}] {workload}: p50={stats.p50_ms}ms p95={stats.p95_ms}ms "
          f"(n={stats.n}, failures={stats.failures})")
