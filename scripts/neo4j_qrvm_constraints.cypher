// Constraints for QRVM/RVL/RSL entities
CREATE CONSTRAINT rogue_event_id IF NOT EXISTS
FOR (e:RogueEvent) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT rogue_direction_id IF NOT EXISTS
FOR (d:RogueDirection) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT qms_state_id IF NOT EXISTS
FOR (q:QMSState) REQUIRE q.id IS UNIQUE;
