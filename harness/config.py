"""
Central config for the benchmark suite.

Every platform is defined here with:
  - env vars it needs (never hardcode credentials)
  - the *documented* free-tier resource specs (for the fairness table in the README)
  - which query dialect its loader/workload files should use

Fill in the ??? fields once you've provisioned each instance and re-verified
the current specs on each platform's pricing/docs page (they change).
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass

# Load .env from the project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass
class PlatformSpec:
    name: str
    dialect: str  # "cypher" | "aql" | "gremlin"
    vcpu: str
    ram: str
    disk: str
    tier_type: str  # "always-free" | "trial-Ndays"
    notes: str = ""
    env_prefix: str = ""


PLATFORMS = {
    "cognodb": PlatformSpec(
        name="CognoDB Cloud",
        dialect="cypher",
        vcpu="0.5 (burstable)",
        ram="256 MB",
        disk="1 GB",
        tier_type="always-free",
        notes="Baseline. bolt+s:// URI, user 'cognodb'.",
        env_prefix="COGNODB",
    ),
    "neo4j": PlatformSpec(
        name="Neo4j AuraDB Free",
        dialect="cypher",
        vcpu="??? (verify at provisioning time)",
        ram="??? (verify at provisioning time)",
        disk="200k nodes / 400k rels cap (not GB-based)",
        tier_type="always-free",
        notes="Closest protocol match to CognoDB (both Bolt/Cypher). "
              "Verify node/relationship cap fits the chosen dataset sample.",
        env_prefix="NEO4J",
    ),
    "arangodb": PlatformSpec(
        name="ArangoDB Oasis",
        dialect="aql",
        vcpu="??? (verify at provisioning time)",
        ram="??? (verify at provisioning time)",
        disk="??? (verify at provisioning time)",
        tier_type="trial-14days",
        notes="14-day clock starts at signup. Provision early; run this leg first.",
        env_prefix="ARANGO",
    ),
    "memgraph": PlatformSpec(
        name="Memgraph Cloud",
        dialect="cypher",
        vcpu="??? (verify at provisioning time)",
        ram="2 GB (documented cap)",
        disk="??? (verify at provisioning time)",
        tier_type="trial-14days",
        notes="RAM cap (2GB) is well above CognoDB's 256MB baseline -- "
              "flag explicitly in README fairness section. "
              "14-day clock starts at signup; run this leg first.",
        env_prefix="MEMGRAPH",
    ),
    "neptune": PlatformSpec(
        name="Amazon Neptune",
        dialect="gremlin",
        vcpu="2 (db.t3.medium)",
        ram="4 GB (db.t3.medium)",
        disk="1 GB / 10M I/O requests",
        tier_type="trial-30days",
        notes="Largest resource mismatch vs CognoDB baseline (2 vCPU/4GB vs "
              "0.5vCPU/256MB). Must be called out explicitly as a methodology "
              "caveat per assignment section 5.3. Uses openCypher or Gremlin -- "
              "pick one dialect and note the choice.",
        env_prefix="NEPTUNE",
    ),
    "falkordb": PlatformSpec(
        name="FalkorDB Cloud",
        dialect="cypher",
        vcpu="1",
        ram="100 MB (documented cap)",
        disk="100 MB",
        tier_type="always-free",
        notes="Free tier RAM cap (100MB) is below CognoDB's 256MB baseline.",
        env_prefix="FALKORDB",
    ),
}


def get_env(prefix: str, key: str, required: bool = True) -> str:
    """Read PREFIX_KEY from env, e.g. get_env('COGNODB', 'URI') -> COGNODB_URI."""
    name = f"{prefix}_{key}"
    val = os.environ.get(name)
    if required and not val:
        raise RuntimeError(
            f"Missing required env var {name}. Copy .env.example to .env "
            f"and fill it in, or export it in your shell."
        )
    return val
