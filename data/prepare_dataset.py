import random
from pathlib import Path

import pandas as pd

# ----------------------------
# Configuration
# ----------------------------

INPUT_FILE = "soc-pokec-relationships.txt"

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

EDGE_LIMIT = 300000          # choose between 100000 and 500000
SAMPLE_SIZE = 1000

# ----------------------------
# Read dataset
# ----------------------------

edges = pd.read_csv(
    INPUT_FILE,
    sep="\t",
    comment="#",
    header=None,
    names=["src", "dst"]
)

print(f"Original edges: {len(edges):,}")

# Keep first N edges
edges = edges.iloc[:EDGE_LIMIT].copy()

print(f"Using edges: {len(edges):,}")

# ----------------------------
# Extract nodes
# ----------------------------

nodes = pd.unique(
    pd.concat([edges["src"], edges["dst"]], ignore_index=True)
)

nodes = pd.DataFrame({"id": nodes})

print(f"Nodes: {len(nodes):,}")

# ----------------------------
# Save nodes.csv
# ----------------------------

nodes.to_csv(
    OUTPUT_DIR / "nodes.csv",
    index=False
)

# ----------------------------
# Save edges.csv
# ----------------------------

edges.to_csv(
    OUTPUT_DIR / "edges.csv",
    index=False
)

# ----------------------------
# Sample IDs
# ----------------------------

sample_size = min(SAMPLE_SIZE, len(nodes))

sample_ids = random.sample(
    nodes["id"].tolist(),
    sample_size
)

with open(OUTPUT_DIR / "sample_ids.txt", "w") as f:
    for node in sample_ids:
        f.write(f"{node}\n")

print("Done!")
print(f"nodes.csv -> {OUTPUT_DIR/'nodes.csv'}")
print(f"edges.csv -> {OUTPUT_DIR/'edges.csv'}")
print(f"sample_ids.txt -> {OUTPUT_DIR/'sample_ids.txt'}")