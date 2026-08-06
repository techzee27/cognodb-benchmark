"""
Read-workload runner for ArangoDB Oasis: 1/2/3-hop traversals, point lookup,
filtered lookup, and a group-by aggregation using AQL.

Usage:
    python -m workloads.workload_arangodb --sample-ids data/sample_ids.txt --iterations 100
"""

import argparse
import random
import sys
from pathlib import Path

from arango import ArangoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env
from harness.metrics import run_warmed_up, save_result

PLATFORM = "arangodb"


def get_db():
    url = get_env("ARANGO", "URL")
    user = get_env("ARANGO", "USER", required=False) or "root"
    password = get_env("ARANGO", "PASSWORD")
    db_name = get_env("ARANGO", "DB", required=False) or "benchmark"

    client = ArangoClient(hosts=url)
    return client.db(db_name, username=user, password=password)


def load_sample_ids(path: str, n: int = 50) -> list[str]:
    with open(path) as f:
        ids = [line.strip() for line in f if line.strip()]
    return random.sample(ids, min(n, len(ids)))


def run_traversals(db, sample_ids: list[str], iterations: int, warmup: int):
    queries = {
        "1hop": (
            "FOR n IN nodes FILTER n.id == @id "
            "FOR v IN 1..1 OUTBOUND n edges "
            "COLLECT WITH COUNT INTO cnt RETURN cnt"
        ),
        "2hop": (
            "FOR n IN nodes FILTER n.id == @id "
            "FOR v IN 2..2 OUTBOUND n edges "
            "COLLECT WITH COUNT INTO cnt RETURN cnt"
        ),
        "3hop": (
            "FOR n IN nodes FILTER n.id == @id "
            "FOR v IN 3..3 OUTBOUND n edges "
            "COLLECT WITH COUNT INTO cnt RETURN cnt"
        ),
    }
    for label, aql in queries.items():
        def fn(aql=aql):
            node_id = str(random.choice(sample_ids))
            cursor = db.aql.execute(aql, bind_vars={"id": node_id})
            list(cursor)

        stats = run_warmed_up(fn, iterations=iterations, warmup=warmup)
        save_result(PLATFORM, f"traversal_{label}", stats)


def run_lookups(db, sample_ids: list[str], iterations: int, warmup: int):
    def point_lookup():
        node_id = str(random.choice(sample_ids))
        cursor = db.aql.execute(
            "FOR n IN nodes FILTER n.id == @id RETURN n",
            bind_vars={"id": node_id},
        )
        list(cursor)

    stats = run_warmed_up(point_lookup, iterations=iterations, warmup=warmup)
    save_result(
        PLATFORM,
        "point_lookup",
        stats,
        extra={"indexed_property": "id (persistent index / _key)"},
    )

    def filtered_lookup():
        node_id = str(random.choice(sample_ids))
        cursor = db.aql.execute(
            "FOR n IN nodes FILTER n.id == @id "
            "FOR v IN 1..1 OUTBOUND n edges "
            "LIMIT 25 RETURN v",
            bind_vars={"id": node_id},
        )
        list(cursor)

    stats = run_warmed_up(filtered_lookup, iterations=iterations, warmup=warmup)
    save_result(PLATFORM, "filtered_lookup", stats)


def run_aggregation(db, iterations: int, warmup: int):
    def agg():
        cursor = db.aql.execute(
            "FOR e IN edges COLLECT WITH COUNT INTO degree_sum RETURN degree_sum"
        )
        list(cursor)

    stats = run_warmed_up(agg, iterations=min(iterations, 30), warmup=min(warmup, 5))
    save_result(PLATFORM, "aggregation_count", stats)


def run_mixed(sample_ids: list[str]):
    from workloads.mixed_workload import run_mixed_workload

    def read_op(db):
        node_id = str(random.choice(sample_ids))
        cursor = db.aql.execute(
            "FOR n IN nodes FILTER n.id == @id "
            "FOR v IN 1..1 OUTBOUND n edges "
            "COLLECT WITH COUNT INTO cnt RETURN cnt",
            bind_vars={"id": node_id},
        )
        list(cursor)

    def write_op(db):
        node_id = str(random.choice(sample_ids))
        db.aql.execute(
            "FOR n IN nodes FILTER n.id == @id UPDATE n WITH { last_accessed: DATE_NOW() } IN nodes",
            bind_vars={"id": node_id},
        )

    run_mixed_workload(
        platform=PLATFORM,
        make_client=get_db,
        read_op=read_op,
        write_op=write_op,
        read_write_ratio=0.9,
        concurrency_levels=[1, 10, 40],
        duration_seconds=15,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-ids", required=True)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()

    db = get_db()
    ids = load_sample_ids(args.sample_ids)

    run_traversals(db, ids, args.iterations, args.warmup)
    run_lookups(db, ids, args.iterations, args.warmup)
    run_aggregation(db, args.iterations, args.warmup)

    run_mixed(ids)
    print(f"Done. See results/{PLATFORM}.json")
