"""
Read-workload runner for FalkorDB Cloud: 1/2/3-hop traversals, point lookup,
filtered lookup, and a group-by aggregation using Cypher via falkordb driver.

Usage:
    python -m workloads.workload_falkordb --sample-ids data/sample_ids.txt --iterations 100
"""

import argparse
import random
import sys
from pathlib import Path

from falkordb import FalkorDB

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env
from harness.metrics import run_warmed_up, save_result

PLATFORM = "falkordb"


def get_graph():
    url = get_env("FALKORDB", "URL", required=False)
    host = get_env("FALKORDB", "HOST", required=False) or "localhost"

    timeout_kwargs = {
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    }

    if url:
        db = FalkorDB.from_url(url, **timeout_kwargs)
    elif host.startswith("redis://") or host.startswith("rediss://"):
        db = FalkorDB.from_url(host, **timeout_kwargs)
    else:
        port = int(get_env("FALKORDB", "PORT", required=False) or 6379)
        user = get_env("FALKORDB", "USER", required=False) or None
        password = get_env("FALKORDB", "PASSWORD", required=False) or None
        ssl_env = get_env("FALKORDB", "SSL", required=False)

        if ssl_env is not None:
            is_ssl = ssl_env.lower() in ("true", "1", "yes")
            db = FalkorDB(
                host=host,
                port=port,
                username=user,
                password=password,
                ssl=is_ssl,
                **timeout_kwargs
            )
        else:
            try:
                db = FalkorDB(
                    host=host,
                    port=port,
                    username=user,
                    password=password,
                    ssl=False,
                    **timeout_kwargs
                )
            except Exception:
                db = FalkorDB(
                    host=host,
                    port=port,
                    username=user,
                    password=password,
                    ssl=True,
                    **timeout_kwargs
                )

    graph_name = get_env("FALKORDB", "GRAPH", required=False) or "benchmark"
    return db.select_graph(graph_name)


def load_sample_ids(path: str, n: int = 50) -> list[str]:
    with open(path) as f:
        ids = [line.strip() for line in f if line.strip()]
    return random.sample(ids, min(n, len(ids)))


def run_traversals(graph, sample_ids: list[str], iterations: int, warmup: int):
    queries = {
        "1hop": "MATCH (n:Node {id: $id})-[:CONNECTS]->(m) RETURN count(m)",
        "2hop": "MATCH (n:Node {id: $id})-[:CONNECTS]->()-[:CONNECTS]->(m) RETURN count(m)",
        "3hop": "MATCH (n:Node {id: $id})-[:CONNECTS]->()-[:CONNECTS]->()-[:CONNECTS]->(m) RETURN count(m)",
    }
    for label, cypher in queries.items():
        def fn(cypher=cypher):
            node_id = random.choice(sample_ids)
            graph.query(cypher, params={"id": node_id})

        stats = run_warmed_up(fn, iterations=iterations, warmup=warmup)
        save_result(PLATFORM, f"traversal_{label}", stats)


def run_lookups(graph, sample_ids: list[str], iterations: int, warmup: int):
    def point_lookup():
        node_id = random.choice(sample_ids)
        graph.query("MATCH (n:Node {id: $id}) RETURN n", params={"id": node_id})

    stats = run_warmed_up(point_lookup, iterations=iterations, warmup=warmup)
    save_result(PLATFORM, "point_lookup", stats,
                 extra={"indexed_property": "id (attribute index)"})

    def filtered_lookup():
        node_id = random.choice(sample_ids)
        graph.query(
            "MATCH (n:Node)-[:CONNECTS]->(m) WHERE n.id = $id RETURN m LIMIT 25",
            params={"id": node_id},
        )

    stats = run_warmed_up(filtered_lookup, iterations=iterations, warmup=warmup)
    save_result(PLATFORM, "filtered_lookup", stats)


def run_aggregation(graph, iterations: int, warmup: int):
    def agg():
        graph.query(
            "MATCH (n:Node)-[:CONNECTS]->(m) "
            "RETURN count(*) AS degree_sum"
        )

    stats = run_warmed_up(agg, iterations=min(iterations, 30), warmup=min(warmup, 5))
    save_result(PLATFORM, "aggregation_count", stats)


def run_mixed(sample_ids: list[str]):
    from workloads.mixed_workload import run_mixed_workload

    def read_op(graph):
        node_id = random.choice(sample_ids)
        graph.query("MATCH (n:Node {id: $id})-[:CONNECTS]->(m) RETURN count(m)", params={"id": node_id})

    def write_op(graph):
        node_id = random.choice(sample_ids)
        graph.query("MATCH (n:Node {id: $id}) SET n.last_accessed = timestamp()", params={"id": node_id})

    run_mixed_workload(
        platform=PLATFORM,
        make_client=get_graph,
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

    graph = get_graph()
    ids = load_sample_ids(args.sample_ids)

    run_traversals(graph, ids, args.iterations, args.warmup)
    run_lookups(graph, ids, args.iterations, args.warmup)
    run_aggregation(graph, args.iterations, args.warmup)

    run_mixed(ids)
    print(f"Done. See results/{PLATFORM}.json")
