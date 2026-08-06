## Latency results

| Platform | Metric | p50 (ms) | p95 (ms) | n | failures |
|---|---|---|---|---|---|
| arangodb | traversal_1hop | 266.476 | 333.812 | 100 | 0 |
| arangodb | traversal_2hop | 268.392 | 334.493 | 100 | 0 |
| arangodb | traversal_3hop | 270.003 | 349.34 | 100 | 0 |
| arangodb | point_lookup | 258.61 | 346.614 | 100 | 0 |
| arangodb | filtered_lookup | 265.48 | 344.828 | 100 | 0 |
| arangodb | aggregation_count | 788.328 | 1220.898 | 30 | 0 |
| cognodb | traversal_1hop | 250.271 | 309.382 | 100 | 0 |
| cognodb | traversal_2hop | 250.183 | 307.795 | 100 | 0 |
| cognodb | traversal_3hop | 250.081 | 310.587 | 100 | 0 |
| cognodb | point_lookup | 250.353 | 307.958 | 100 | 0 |
| cognodb | filtered_lookup | 250.583 | 254.736 | 100 | 0 |
| cognodb | aggregation_count | 704.918 | 787.523 | 30 | 0 |
| falkordb | traversal_1hop | 18.103 | 18.67 | 100 | 0 |
| falkordb | traversal_2hop | 18.091 | 18.4 | 100 | 0 |
| falkordb | traversal_3hop | 18.07 | 19.549 | 100 | 0 |
| falkordb | point_lookup | 18.038 | 20.432 | 100 | 0 |
| falkordb | filtered_lookup | 18.066 | 22.633 | 100 | 0 |
| falkordb | aggregation_count | 201.736 | 231.849 | 30 | 0 |
| memgraph | traversal_1hop | 148.056 | 157.136 | 100 | 0 |
| memgraph | traversal_2hop | 148.055 | 153.436 | 100 | 0 |
| memgraph | traversal_3hop | 148.051 | 148.893 | 100 | 0 |
| memgraph | point_lookup | 148.008 | 148.795 | 100 | 0 |
| memgraph | filtered_lookup | 148.067 | 149.041 | 100 | 0 |
| memgraph | aggregation_count | 194.962 | 218.502 | 30 | 0 |
| neo4j | traversal_1hop | 52.398 | 62.357 | 100 | 0 |
| neo4j | traversal_2hop | 52.58 | 88.575 | 100 | 0 |
| neo4j | traversal_3hop | 52.523 | 66.036 | 100 | 0 |
| neo4j | point_lookup | 52.685 | 62.342 | 100 | 0 |
| neo4j | filtered_lookup | 52.539 | 61.106 | 100 | 0 |
| neo4j | aggregation_count | 52.595 | 64.805 | 30 | 0 |

## Mixed workload results

| Platform | Concurrency | Throughput (ops/s) | Reads | Writes | Failures |
|---|---|---|---|---|---|
| arangodb | 1 | 3.4 | 45 | 7 | 0 |
| arangodb | 10 | 34.7 | 471 | 57 | 0 |
| arangodb | 40 | 116.2 | 1620 | 156 | 0 |
| cognodb | 1 | 3.2 | 43 | 6 | 0 |
| cognodb | 10 | 34.2 | 469 | 52 | 0 |
| cognodb | 40 | 124.7 | 1736 | 168 | 3 |
| falkordb | 1 | 53.1 | 711 | 86 | 0 |
| falkordb | 10 | 536.8 | 7209 | 863 | 0 |
| falkordb | 40 | 2030.1 | 27422 | 3066 | 0 |
| memgraph | 1 | 6.3 | 86 | 8 | 0 |
| memgraph | 10 | 63.1 | 864 | 91 | 0 |
| memgraph | 40 | 247.3 | 3399 | 347 | 0 |
| neo4j | 1 | 9.1 | 124 | 13 | 0 |
| neo4j | 10 | 86.8 | 1180 | 129 | 0 |
| neo4j | 40 | 331.8 | 4541 | 479 | 0 |
