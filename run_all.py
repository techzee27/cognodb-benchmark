"""
One-command orchestrator: loads dataset and executes read/mixed workloads
for every specified graph database platform, then outputs metric summaries.

Usage:
    python run_all.py --platforms cognodb neo4j arangodb memgraph falkordb \
        --nodes data/nodes.csv --edges data/edges.csv --sample-ids data/sample_ids.txt

    python run_all.py --platforms falkordb --skip-load
"""

import argparse
import subprocess
import sys
import time

ALL_PLATFORMS = ["cognodb", "neo4j", "arangodb", "memgraph", "falkordb"]


def run_platform(
    platform: str,
    nodes: str,
    edges: str,
    sample_ids: str,
    iterations: int,
    warmup: int,
    skip_load: bool,
) -> None:
    """Execute data loading and workload benchmark for a target database platform.

    Args:
        platform: Target platform identifier (e.g. 'cognodb', 'falkordb').
        nodes: Path to nodes CSV.
        edges: Path to edges CSV.
        sample_ids: Path to sample node IDs file.
        iterations: Number of query benchmark iterations.
        warmup: Number of warmup query iterations.
        skip_load: If True, bypasses data loading step.
    """
    print(f"\n{'=' * 60}\nRunning Benchmark for: {platform.upper()}\n{'=' * 60}")

    if not skip_load:
        t0 = time.perf_counter()
        loader_mod = f"loaders.load_{platform}"
        subprocess.run(
            [sys.executable, "-m", loader_mod, "--nodes", nodes, "--edges", edges],
            check=True,
        )
        print(f"[{platform}] Data loading completed in {time.perf_counter() - t0:.1f}s total.")
    else:
        print(f"[{platform}] Bypassing data load (--skip-load flag set).")

    workload_mod = f"workloads.workload_{platform}"
    subprocess.run(
        [
            sys.executable, "-m", workload_mod,
            "--sample-ids", sample_ids,
            "--iterations", str(iterations),
            "--warmup", str(warmup),
        ],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark suite orchestrator across graph databases")
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=ALL_PLATFORMS,
        choices=ALL_PLATFORMS,
        help="List of platforms to benchmark",
    )
    parser.add_argument("--nodes", default="data/nodes.csv", help="Path to nodes CSV file")
    parser.add_argument("--edges", default="data/edges.csv", help="Path to edges CSV file")
    parser.add_argument("--sample-ids", default="data/sample_ids.txt", help="Path to sample IDs file")
    parser.add_argument("--iterations", type=int, default=100, help="Number of query iterations")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup iterations")
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Reuse already-loaded data; only execute workload benchmarks",
    )
    args = parser.parse_args()

    for platform in args.platforms:
        try:
            run_platform(
                platform,
                args.nodes,
                args.edges,
                args.sample_ids,
                args.iterations,
                args.warmup,
                args.skip_load,
            )
        except subprocess.CalledProcessError as e:
            print(f"!! Execution failed for {platform}: {e}. Proceeding with remaining platforms.")
            continue

    print("\n" + "=" * 60)
    print("All platform benchmark runs completed.")
    print("Results saved in results/*.json")
    print("To generate markdown report tables and visual charts, run:")
    print("  python -m harness.build_report")
    print("=" * 60)
