"""
TODO: Loader for neptune -- copy the structure of loaders/load_cognodb.py.

Steps to port:
  1. Swap the neo4j driver import for this platform's client
     (arango: ArangoClient from arango; neptune: gremlin_python client;
      memgraph: neo4j driver works as-is, Memgraph speaks Bolt/Cypher too).
  2. Keep identical batch size, identical CSV parsing, identical
     node/edge counts -- only the query syntax should change
     (AQL for arango, Gremlin steps for neptune, Cypher for memgraph).
  3. Return the same dict shape: node_count, rel_count, total_seconds,
     node_throughput_per_s, rel_throughput_per_s -- build_report.py
     and the README table assume this shape.
  4. Use harness.config.get_env("NEPTUNE", "...") for credentials, matching
     the env vars documented in .env.example.
"""

raise NotImplementedError("Port loaders/load_cognodb.py to neptune -- see docstring above")
