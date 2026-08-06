"""
Load the dataset into CognoDB Cloud via the official Neo4j driver
(CognoDB speaks the Bolt protocol / Cypher, per the setup doc).

This is the reference/template loader -- get this one fully correct
before copying the pattern to the other 4 platforms.

Usage:
    python -m loaders.load_cognodb --nodes data/nodes.csv --edges data/edges.csv
"""

import argparse
import csv
import time
import sys
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env

BATCH_SIZE = 1000


def load(nodes_path: str, edges_path: str) -> dict[str, float | int]:
    """Load nodes and edges CSV files into CognoDB Cloud in batches.

    Args:
        nodes_path: Path to nodes CSV (column: id)
        edges_path: Path to edges CSV (columns: src, dst)

    Returns:
        Dictionary containing counts, wall-clock time, and throughput metrics.
    """
    uri = get_env("COGNODB", "URI")
    user = get_env("COGNODB", "USER", required=False) or "cognodb"
    password = get_env("COGNODB", "PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    node_count = 0
    rel_count = 0
    t_start = time.perf_counter()

    with driver.session() as session:
        # Create unique constraint for fast node lookups by id
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE")

        # --- Load nodes in 1,000-row batches ---
        with open(nodes_path) as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append({"id": row["id"]})
                if len(batch) >= BATCH_SIZE:
                    session.run(
                        "UNWIND $batch AS row MERGE (n:Node {id: row.id})",
                        batch=batch,
                    )
                    node_count += len(batch)
                    batch = []
            if batch:
                session.run(
                    "UNWIND $batch AS row MERGE (n:Node {id: row.id})",
                    batch=batch,
                )
                node_count += len(batch)

        t_nodes_done = time.perf_counter()

        # --- Load relationships in 1,000-row batches ---
        with open(edges_path) as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append({"src": row["src"], "dst": row["dst"]})
                if len(batch) >= BATCH_SIZE:
                    session.run(
                        "UNWIND $batch AS row "
                        "MATCH (a:Node {id: row.src}), (b:Node {id: row.dst}) "
                        "MERGE (a)-[:CONNECTS]->(b)",
                        batch=batch,
                    )
                    rel_count += len(batch)
                    batch = []
            if batch:
                session.run(
                    "UNWIND $batch AS row "
                    "MATCH (a:Node {id: row.src}), (b:Node {id: row.dst}) "
                    "MERGE (a)-[:CONNECTS]->(b)",
                    batch=batch,
                )
                rel_count += len(batch)

    t_end = time.perf_counter()
    driver.close()

    total_time = t_end - t_start
    node_time = t_nodes_done - t_start
    rel_time = t_end - t_nodes_done

    node_throughput = round(node_count / node_time, 1) if node_time > 0 else 0.0
    rel_throughput = round(rel_count / rel_time, 1) if rel_time > 0 else 0.0

    print(f"CognoDB load complete: {node_count} nodes, {rel_count} relationships")
    print(f"Total wall-clock: {total_time:.2f}s")
    print(f"Node throughput: {node_throughput} nodes/s")
    print(f"Rel throughput:  {rel_throughput} rels/s")

    return {
        "node_count": node_count,
        "rel_count": rel_count,
        "total_seconds": round(total_time, 2),
        "node_throughput_per_s": node_throughput,
        "rel_throughput_per_s": rel_throughput,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load graph data into CognoDB Cloud")
    parser.add_argument("--nodes", required=True, help="CSV with column: id")
    parser.add_argument("--edges", required=True, help="CSV with columns: src,dst")
    args = parser.parse_args()
    load(args.nodes, args.edges)
