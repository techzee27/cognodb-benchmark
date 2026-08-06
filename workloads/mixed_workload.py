"""
Concurrent mixed read/write workload -- generic runner driven by a
platform-specific `client_factory` and `op` function, so it can be reused
across all 5 platforms without duplicating the concurrency logic.

Run a sweep across concurrency levels (1/10/40 clients is the assignment's
suggested range) with a stated read/write mix, and report sustained
queries/second.

Usage (as a library, called from each platform's workload file):

    from workloads.mixed_workload import run_mixed_workload

    run_mixed_workload(
        platform="cognodb",
        make_client=get_driver,          # returns a fresh client/session-maker
        read_op=my_read_fn,               # takes a client, does one read
        write_op=my_write_fn,             # takes a client, does one write
        read_write_ratio=0.9,             # 90% reads / 10% writes
        concurrency_levels=[1, 10, 40],
        duration_seconds=15,
    )
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from harness.metrics import save_result, LatencyStats


@dataclass
class MixedResult:
    concurrency: int
    duration_s: float
    total_ops: int
    reads: int
    writes: int
    failures: int
    throughput_ops_per_s: float


def _worker(client, read_op, write_op, read_write_ratio, stop_time, counters, lock):
    local_ops = 0
    local_reads = 0
    local_writes = 0
    local_failures = 0
    while time.perf_counter() < stop_time:
        is_read = random.random() < read_write_ratio
        try:
            if is_read:
                read_op(client)
                local_reads += 1
            else:
                write_op(client)
                local_writes += 1
            local_ops += 1
        except Exception:
            local_failures += 1
    with lock:
        counters["ops"] += local_ops
        counters["reads"] += local_reads
        counters["writes"] += local_writes
        counters["failures"] += local_failures


def run_mixed_workload(
    platform: str,
    make_client,
    read_op,
    write_op,
    read_write_ratio: float = 0.9,
    concurrency_levels: list[int] = (1, 10, 40),
    duration_seconds: int = 15,
):
    import threading

    all_results = {}
    for concurrency in concurrency_levels:
        clients = [make_client() for _ in range(concurrency)]
        counters = {"ops": 0, "reads": 0, "writes": 0, "failures": 0}
        lock = threading.Lock()
        stop_time = time.perf_counter() + duration_seconds

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [
                pool.submit(_worker, clients[i], read_op, write_op,
                            read_write_ratio, stop_time, counters, lock)
                for i in range(concurrency)
            ]
            for f in futures:
                f.result()
        elapsed = time.perf_counter() - t0

        result = MixedResult(
            concurrency=concurrency,
            duration_s=round(elapsed, 2),
            total_ops=counters["ops"],
            reads=counters["reads"],
            writes=counters["writes"],
            failures=counters["failures"],
            throughput_ops_per_s=round(counters["ops"] / elapsed, 1),
        )
        all_results[f"c{concurrency}"] = result.__dict__
        print(f"[{platform}] mixed workload @ {concurrency} clients: "
              f"{result.throughput_ops_per_s} ops/s "
              f"({result.reads} reads / {result.writes} writes, "
              f"{result.failures} failures)")

    # Save as a single record (not LatencyStats-shaped, so write directly)
    import json
    from pathlib import Path
    Path("results").mkdir(exist_ok=True)
    out_path = Path("results") / f"{platform}.json"
    data = json.loads(out_path.read_text()) if out_path.exists() else {}
    data["mixed_workload"] = {
        "read_write_ratio": read_write_ratio,
        "duration_seconds_per_level": duration_seconds,
        "levels": all_results,
    }
    out_path.write_text(json.dumps(data, indent=2))
    return all_results
