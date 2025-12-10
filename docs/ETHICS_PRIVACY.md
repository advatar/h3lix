## Ethics & Privacy (H3LIX/LAIZA Demo)

- Default data is synthetic; no real human traces shipped.  
- For any real human use:
  - Obtain IRB/ethics approval and explicit consent for multimodal data (somatic, behavioral, text).
  - Use pseudonymous participant IDs; store any identifying info separately.
  - Define retention/deletion policies and communicate them to participants.
  - Restrict access (roles) to participant-linked graphs and somatic summaries.
  - Keep an audit trail of MPG edits, MUFS results, and policy actions (aligns with governance role of RVs).
- Do not merge or publish real human data in this repo. Replace the demo credentials (`neo4j/neo4j-password`) for any production or shared deployment.
