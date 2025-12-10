"""
Create Neo4j constraints for protocol personalization entities.
"""

from __future__ import annotations

import os

from neo4j import GraphDatabase


def main() -> None:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j-password")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    statements = [
        "CREATE CONSTRAINT protocol_instance_id IF NOT EXISTS FOR (p:ProtocolInstance) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT module_state_id IF NOT EXISTS FOR (m:ModuleState) REQUIRE m.id IS UNIQUE",
        "CREATE CONSTRAINT step_state_id IF NOT EXISTS FOR (s:StepState) REQUIRE s.id IS UNIQUE",
    ]
    with driver.session() as session:
        for stmt in statements:
            session.run(stmt)
    driver.close()


if __name__ == "__main__":
    main()
