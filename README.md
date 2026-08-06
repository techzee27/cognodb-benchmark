# cognodb-benchmark

A standardized, multi-database benchmarking suite for evaluating graph database performance across **CognoDB Cloud**, **Neo4j AuraDB**, **ArangoDB Oasis**, **Memgraph Cloud**, **FalkorDB Cloud**, and **Amazon Neptune**.

The suite measures data loading times, multi-hop graph traversal latencies, filtered lookups, aggregation throughput, and concurrent read/write mixed workloads under real-world network conditions.

---

## Architecture & Platform Specifications

| Platform | Dialect / Protocol | vCPU | RAM | Disk / Storage | Tier Type | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CognoDB Cloud** | Bolt / Cypher | 0.5 (burstable) | 256 MB | 1 GB | Always Free | Baseline target platform |
| **Neo4j AuraDB** | Bolt / Cypher | Shared | Shared | 200k nodes / 400k rels cap | Always Free | Direct Bolt/Cypher protocol match |
| **ArangoDB Oasis** | HTTP / AQL | Shared | Shared | Shared | 14-day Trial | Multi-model document & graph engine |
| **Memgraph Cloud** | Bolt / Cypher | Shared | 2 GB | Shared | 14-day Trial | In-memory graph engine |
| **FalkorDB Cloud** | Redis / Cypher | 1 vCPU | 100 MB | 100 MB | Always Free | Redis module graph engine |
| **Amazon Neptune** | Gremlin / openCypher | 2 vCPU (`db.t3.medium`) | 4 GB | 1 GB / 10M I/O | 30-day Trial | AWS managed graph service |

> [!NOTE]
> Resource allocation differences across free/trial tiers (e.g. 256MB baseline vs 2GB/4GB instances) are noted in methodology evaluations.

---

## Directory Structure

```text
cognodb-benchmark/
├── README.md                 # Project documentation and quickstart guide
├── requirements.txt          # Python dependencies
├── run_all.py                # End-to-end benchmark orchestrator CLI
├── .env.example              # Template for database connection secrets
├── data/
│   ├── prepare_dataset.py    # Subgraph extractor & ID sampler
│   ├── nodes.csv             # Generated graph nodes
│   ├── edges.csv             # Generated graph edges
│   └── sample_ids.txt        # Sampled target node IDs for queries
├── harness/
│   ├── config.py             # Platform specifications & environment loader
│   ├── metrics.py            # Latency, percentile (p50/p95), and TPS metrics
│   └── build_report.py       # Markdown matrix generator & plot generator
├── loaders/                  # Bulk data loading modules per platform
│   ├── load_cognodb.py
│   ├── load_neo4j.py
│   ├── load_arangodb.py
│   ├── load_memgraph.py
│   ├── load_falkordb.py
│   └── load_neptune.py
├── workloads/                # Benchmark workload query suites per platform
│   ├── workload_cognodb.py
│   ├── workload_neo4j.py
│   ├── workload_arangodb.py
│   ├── workload_memgraph.py
│   ├── workload_falkordb.py
│   ├── workload_neptune.py
│   └── mixed_workload.py     # Concurrent multi-threaded read/write stress tester
├── docs/
│   └── results_matrix.md     # Benchmark output metrics summary
├── UI_review/                # Platform web UI & admin dashboard screenshots
│   ├── Cogno_DB/
│   ├── Neo4j_DB/
│   ├── Arango_DB/
│   ├── Memgraph_DB/
│   └── Falkor_DB/
└── results/                  # Execution output raw JSON benchmarks
```

---

## Prerequisites & Installation

1. **Python 3.10+** is required.
2. Clone the repository and create a virtual environment:

```bash
git clone https://github.com/techzee27/cognodb-benchmark.git
cd cognodb-benchmark

python3 -m venv .venv
source .venv/bin/activate
```

3. Install required Python packages:

```bash
pip install -r requirements.txt
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in your connection URIs, ports, usernames, and passwords for each target platform:

```bash
cp .env.example .env
```

Example `.env` configuration:

```env
# CognoDB Cloud
COGNODB_URI=bolt+s://<instance-id>.databases.cognodb.cloud
COGNODB_PASSWORD=your_password

# Neo4j AuraDB Free
NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# ArangoDB Oasis
ARANGO_URL=https://<deployment>.arangodb.cloud:8529
ARANGO_USER=root
ARANGO_PASSWORD=your_password
ARANGO_DB=benchmark

# Memgraph Cloud
MEMGRAPH_URI=bolt://<instance>.memgraph.cloud:7687
MEMGRAPH_USER=
MEMGRAPH_PASSWORD=your_password

# FalkorDB Cloud
FALKORDB_HOST=<instance-host>.falkordb.cloud
FALKORDB_PORT=6379
FALKORDB_USER=
FALKORDB_PASSWORD=your_password
FALKORDB_GRAPH=benchmark
```

---

## Data Preparation

The dataset generator processes raw graph edge lists (such as `soc-pokec-relationships.txt`) into formatted node and edge CSV files, while creating a random sample ID file for query benchmarking:

```bash
python data/prepare_dataset.py
```

This generates:
- `data/nodes.csv`
- `data/edges.csv`
- `data/sample_ids.txt`

---

## Running Benchmarks

### 1. Orchestrated Multi-Platform Benchmark

Execute data loading and workload benchmarks across all configured platforms in a single command:

```bash
python run_all.py
```

#### Run Specific Platforms:
```bash
python run_all.py --platforms cognodb neo4j falkordb
```

#### Reuse Existing Loaded Data (Skip Reload Step):
```bash
python run_all.py --platforms cognodb neo4j --skip-load
```

#### Adjust Query Iterations:
```bash
python run_all.py --platforms cognodb --iterations 200 --warmup 20
```

---

### 2. Running Individual Platform Loaders & Workloads

You can also run database loaders and workloads individually:

```bash
# Load data into CognoDB
python -m loaders.load_cognodb --nodes data/nodes.csv --edges data/edges.csv

# Execute workload benchmark on CognoDB
python -m workloads.workload_cognodb --sample-ids data/sample_ids.txt --iterations 100
```

---

## Results & Reporting

Generate the summary report table and results matrix from raw execution logs:

```bash
python -m harness.build_report
```

Output markdown summaries are exported to `docs/results_matrix.md` and raw run metrics are saved under `results/*.json`.

### Benchmark Metrics Matrix

#### Read Latency Benchmarks (ms)

| Platform | Metric | p50 (ms) | p95 (ms) | n | failures |
|---|---|---|---|---|---|
| **FalkorDB** | 1-Hop Traversal | 18.10 | 18.67 | 100 | 0 |
| **FalkorDB** | 2-Hop Traversal | 18.09 | 18.40 | 100 | 0 |
| **FalkorDB** | 3-Hop Traversal | 18.07 | 19.55 | 100 | 0 |
| **Neo4j** | 1-Hop Traversal | 52.40 | 62.36 | 100 | 0 |
| **Neo4j** | 2-Hop Traversal | 52.58 | 88.58 | 100 | 0 |
| **Memgraph** | 1-Hop Traversal | 148.06 | 157.14 | 100 | 0 |
| **CognoDB** | 1-Hop Traversal | 250.27 | 309.38 | 100 | 0 |
| **CognoDB** | Filtered Lookup | 250.58 | 254.74 | 100 | 0 |
| **ArangoDB** | 1-Hop Traversal | 266.48 | 333.81 | 100 | 0 |

#### Concurrent Mixed Workload Throughput (ops/sec)

| Platform | Concurrency (threads) | Throughput (ops/s) | Reads | Writes | Failures |
|---|---|---|---|---|---|
| **FalkorDB** | 40 | 2030.1 | 27,422 | 3,066 | 0 |
| **Neo4j** | 40 | 331.8 | 4,541 | 479 | 0 |
| **Memgraph** | 40 | 247.3 | 3,399 | 347 | 0 |
| **CognoDB** | 40 | 124.7 | 1,736 | 168 | 3 |
| **ArangoDB** | 40 | 116.2 | 1,620 | 156 | 0 |

---

## License

MIT License. See `LICENSE` for details.
