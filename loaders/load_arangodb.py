"""
Load the dataset into ArangoDB Oasis via python-arango.

Usage:
    python -m loaders.load_arangodb --nodes data/nodes.csv --edges data/edges.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path

from arango import ArangoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env

BATCH_SIZE = 1000


def get_db():
    """Connect to ArangoDB instance and return database handle (creating DB if needed)."""
    url = get_env("ARANGO", "URL")
    user = get_env("ARANGO", "USER", required=False) or "root"
    password = get_env("ARANGO", "PASSWORD")
    db_name = get_env("ARANGO", "DB", required=False) or "benchmark"

    client = ArangoClient(hosts=url)

    # Ensure target database exists
    sys_db = client.db("_system", username=user, password=password)
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)

    return client.db(db_name, username=user, password=password)


def load(nodes_path: str, edges_path: str) -> dict[str, float | int]:
    """Load nodes and edges CSV files into ArangoDB document & edge collections in batches.

    Args:
        nodes_path: Path to nodes CSV (column: id)
        edges_path: Path to edges CSV (columns: src, dst)

    Returns:
        Dictionary containing counts, wall-clock time, and throughput metrics.
    """
    db = get_db()

    # Create document collection for nodes
    if not db.has_collection("nodes"):
        nodes_coll = db.create_collection("nodes")
    else:
        nodes_coll = db.collection("nodes")

    # Ensure persistent index on id for fast lookups
    nodes_coll.add_persistent_index(fields=["id"], unique=True)

    # Create edge collection for graph edges
    if not db.has_collection("edges"):
        edges_coll = db.create_collection("edges", edge=True)
    else:
        edges_coll = db.collection("edges")

    node_count = 0
    rel_count = 0
    t_start = time.perf_counter()

    # --- Load nodes in 1,000-row batches ---
    with open(nodes_path) as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            node_id = str(row["id"])
            batch.append({"_key": node_id, "id": node_id})
            if len(batch) >= BATCH_SIZE:
                nodes_coll.insert_many(batch, overwrite_mode="ignore")
                node_count += len(batch)
                batch = []
        if batch:
            nodes_coll.insert_many(batch, overwrite_mode="ignore")
            node_count += len(batch)

    t_nodes_done = time.perf_counter()

    # --- Load edges in 1,000-row batches ---
    with open(edges_path) as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({
                "_from": f"nodes/{row['src']}",
                "_to": f"nodes/{row['dst']}",
            })
            if len(batch) >= BATCH_SIZE:
                edges_coll.insert_many(batch, overwrite_mode="ignore")
                rel_count += len(batch)
                batch = []
        if batch:
            edges_coll.insert_many(batch, overwrite_mode="ignore")
            rel_count += len(batch)

    t_end = time.perf_counter()

    total_time = t_end - t_start
    node_time = t_nodes_done - t_start
    rel_time = t_end - t_nodes_done

    node_throughput = round(node_count / node_time, 1) if node_time > 0 else 0.0
    rel_throughput = round(rel_count / rel_time, 1) if rel_time > 0 else 0.0

    print(f"ArangoDB load complete: {node_count} nodes, {rel_count} relationships")
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
    parser = argparse.ArgumentParser(description="Load graph data into ArangoDB Oasis")
    parser.add_argument("--nodes", required=True, help="CSV with column: id")
    parser.add_argument("--edges", required=True, help="CSV with columns: src,dst")
    args = parser.parse_args()
    load(args.nodes, args.edges)
