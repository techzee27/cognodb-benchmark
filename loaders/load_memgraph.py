"""
Load the dataset into Memgraph Cloud via the Neo4j Bolt driver.

Usage:
    python -m loaders.load_memgraph --nodes data/nodes.csv --edges data/edges.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env

BATCH_SIZE = 1000


def get_driver():
    """Create and return Neo4j/Bolt driver configured for Memgraph Cloud."""
    uri = get_env("MEMGRAPH", "URI")
    # Memgraph Cloud uses self-signed certificates; ensure bolt+ssc:// or neo4j+ssc:// scheme if SSL enabled
    if uri.startswith("bolt://"):
        uri = uri.replace("bolt://", "bolt+ssc://", 1)
    elif uri.startswith("bolt+s://"):
        uri = uri.replace("bolt+s://", "bolt+ssc://", 1)
    elif uri.startswith("neo4j+s://"):
        uri = uri.replace("neo4j+s://", "neo4j+ssc://", 1)

    user = get_env("MEMGRAPH", "USER", required=False) or ""
    password = get_env("MEMGRAPH", "PASSWORD", required=False) or ""
    auth = (user, password) if (user or password) else None
    return GraphDatabase.driver(uri, auth=auth)


def load(nodes_path: str, edges_path: str) -> dict[str, float | int]:
    """Load nodes and edges CSV files into Memgraph Cloud in batches.

    Args:
        nodes_path: Path to nodes CSV (column: id)
        edges_path: Path to edges CSV (columns: src, dst)

    Returns:
        Dictionary containing counts, wall-clock time, and throughput metrics.
    """
    driver = get_driver()
    node_count = 0
    rel_count = 0
    t_start = time.perf_counter()

    with driver.session() as session:
        # Create label index on Node(id) in Memgraph for fast lookups
        try:
            session.run("CREATE INDEX ON :Node(id)")
        except Exception:
            pass

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

    print(f"Memgraph load complete: {node_count} nodes, {rel_count} relationships")
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
    parser = argparse.ArgumentParser(description="Load graph data into Memgraph Cloud")
    parser.add_argument("--nodes", required=True, help="CSV with column: id")
    parser.add_argument("--edges", required=True, help="CSV with columns: src,dst")
    args = parser.parse_args()
    load(args.nodes, args.edges)
