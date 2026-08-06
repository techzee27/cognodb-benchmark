"""
Load the dataset into FalkorDB Cloud via the official falkordb Python client.

Usage:
    python -m loaders.load_falkordb --nodes data/nodes.csv --edges data/edges.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path

from falkordb import FalkorDB

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.config import get_env

BATCH_SIZE = 1000


def get_graph():
    """Create and return FalkorDB Graph client handle with connection auto-fallback."""
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


def load(nodes_path: str, edges_path: str) -> dict[str, float | int]:
    """Load nodes and edges CSV files into FalkorDB Cloud in batches.

    Args:
        nodes_path: Path to nodes CSV (column: id)
        edges_path: Path to edges CSV (columns: src, dst)

    Returns:
        Dictionary containing counts, wall-clock time, and throughput metrics.
    """
    graph = get_graph()

    # Create attribute index on Node(id) for fast lookups
    try:
        graph.query("CREATE INDEX FOR (n:Node) ON (n.id)")
    except Exception:
        pass

    node_count = 0
    rel_count = 0
    t_start = time.perf_counter()

    # --- Load nodes in 1,000-row batches ---
    with open(nodes_path) as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({"id": row["id"]})
            if len(batch) >= BATCH_SIZE:
                graph.query(
                    "UNWIND $batch AS row MERGE (n:Node {id: row.id})",
                    params={"batch": batch},
                )
                node_count += len(batch)
                batch = []
        if batch:
            graph.query(
                "UNWIND $batch AS row MERGE (n:Node {id: row.id})",
                params={"batch": batch},
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
                graph.query(
                    "UNWIND $batch AS row "
                    "MATCH (a:Node {id: row.src}), (b:Node {id: row.dst}) "
                    "MERGE (a)-[:CONNECTS]->(b)",
                    params={"batch": batch},
                )
                rel_count += len(batch)
                batch = []
        if batch:
            graph.query(
                "UNWIND $batch AS row "
                "MATCH (a:Node {id: row.src}), (b:Node {id: row.dst}) "
                "MERGE (a)-[:CONNECTS]->(b)",
                params={"batch": batch},
            )
            rel_count += len(batch)

    t_end = time.perf_counter()

    total_time = t_end - t_start
    node_time = t_nodes_done - t_start
    rel_time = t_end - t_nodes_done

    node_throughput = round(node_count / node_time, 1) if node_time > 0 else 0.0
    rel_throughput = round(rel_count / rel_time, 1) if rel_time > 0 else 0.0

    print(f"FalkorDB load complete: {node_count} nodes, {rel_count} relationships")
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
    parser = argparse.ArgumentParser(description="Load graph data into FalkorDB Cloud")
    parser.add_argument("--nodes", required=True, help="CSV with column: id")
    parser.add_argument("--edges", required=True, help="CSV with columns: src,dst")
    args = parser.parse_args()
    load(args.nodes, args.edges)
