"""
Read-workload runner for CognoDB: 1/2/3-hop traversals, point lookup,
filtered lookup, and a group-by aggregation.

Template for the other platforms -- keep query *logic* identical when you
translate to AQL/Gremlin, only the syntax should differ.

Usage:
    python -m workloads.workload_cognodb --sample-ids data/sample_ids.txt --iterations 100
"""

import argparse
import random
import sys
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env
from harness.metrics import run_warmed_up, save_result

PLATFORM = "cognodb"


def get_driver():
    uri = get_env("COGNODB", "URI")
    password = get_env("COGNODB", "PASSWORD")
    return GraphDatabase.driver(uri, auth=("cognodb", password))


def load_sample_ids(path: str, n: int = 50) -> list[str]:
    with open(path) as f:
        ids = [line.strip() for line in f if line.strip()]
    return random.sample(ids, min(n, len(ids)))


def run_traversals(driver, sample_ids: list[str], iterations: int, warmup: int):
    queries = {
        "1hop": "MATCH (n:Node {id: $id})-[:CONNECTS]->(m) RETURN count(m)",
        "2hop": "MATCH (n:Node {id: $id})-[:CONNECTS]->()-[:CONNECTS]->(m) RETURN count(m)",
        "3hop": "MATCH (n:Node {id: $id})-[:CONNECTS]->()-[:CONNECTS]->()-[:CONNECTS]->(m) RETURN count(m)",
    }
    with driver.session() as session:
        for label, cypher in queries.items():
            def fn(cypher=cypher):
                node_id = random.choice(sample_ids)
                session.run(cypher, id=node_id).consume()

            stats = run_warmed_up(fn, iterations=iterations, warmup=warmup)
            save_result(PLATFORM, f"traversal_{label}", stats)


def run_lookups(driver, sample_ids: list[str], iterations: int, warmup: int):
    with driver.session() as session:
        def point_lookup():
            node_id = random.choice(sample_ids)
            session.run("MATCH (n:Node {id: $id}) RETURN n", id=node_id).consume()

        stats = run_warmed_up(point_lookup, iterations=iterations, warmup=warmup)
        save_result(PLATFORM, "point_lookup", stats,
                     extra={"indexed_property": "id (unique constraint)"})

        def filtered_lookup():
            node_id = random.choice(sample_ids)
            session.run(
                "MATCH (n:Node)-[:CONNECTS]->(m) WHERE n.id = $id RETURN m LIMIT 25",
                id=node_id,
            ).consume()

        stats = run_warmed_up(filtered_lookup, iterations=iterations, warmup=warmup)
        save_result(PLATFORM, "filtered_lookup", stats)


def run_aggregation(driver, iterations: int, warmup: int):
    with driver.session() as session:
        def agg():
            session.run(
                "MATCH (n:Node)-[:CONNECTS]->(m) "
                "RETURN count(*) AS degree_sum"
            ).consume()

        # Aggregations are typically run fewer times since they scan more data;
        # still respect the same warm-up discipline.
        stats = run_warmed_up(agg, iterations=min(iterations, 30), warmup=min(warmup, 5))
        save_result(PLATFORM, "aggregation_count", stats)


def run_mixed(sample_ids: list[str]):
    from workloads.mixed_workload import run_mixed_workload

    def read_op(driver):
        node_id = random.choice(sample_ids)
        with driver.session() as session:
            session.run("MATCH (n:Node {id: $id})-[:CONNECTS]->(m) RETURN count(m)", id=node_id).consume()

    def write_op(driver):
        node_id = random.choice(sample_ids)
        with driver.session() as session:
            session.run("MATCH (n:Node {id: $id}) SET n.last_accessed = timestamp()", id=node_id).consume()

    run_mixed_workload(
        platform=PLATFORM,
        make_client=get_driver,
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

    driver = get_driver()
    ids = load_sample_ids(args.sample_ids)

    run_traversals(driver, ids, args.iterations, args.warmup)
    run_lookups(driver, ids, args.iterations, args.warmup)
    run_aggregation(driver, args.iterations, args.warmup)

    driver.close()

    run_mixed(ids)
    print("Done. See results/cognodb.json")
