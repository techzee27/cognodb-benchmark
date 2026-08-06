"""
TODO: Workload runner for neptune -- copy the structure of
workloads/workload_cognodb.py.

Keep the query *logic* identical to the CognoDB version:
  - 1/2/3-hop traversal from a random sampled start node
  - point lookup by id (state which property is indexed on this platform)
  - filtered/indexed lookup returning up to 25 neighbors
  - a count-style aggregation over the relationship type

Only the query syntax should differ (AQL / Gremlin / Cypher).
Use harness.metrics.run_warmed_up + save_result so results land in the
same results/neptune.json shape the report builder expects.

For the mixed workload, import workloads.mixed_workload.run_mixed_workload
and pass this platform's client factory + read/write op functions.
"""

raise NotImplementedError("Port workloads/workload_cognodb.py to neptune -- see docstring above")
