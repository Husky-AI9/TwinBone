# Threat model

The implementation contract identifies unexpected PHI, cross-subject leakage, prompt
injection, unverified actions, overwritten evidence, duplicate workflows, sensitive logs,
MCP overexposure, consent withdrawal, forged browser scope, hallucination, and concurrent
corrections as primary threats.

Phase 0 mitigations are the synthetic-only data policy, secret exclusions and scan, explicit
component boundaries, and mandatory operating rules. Each later phase must add and test the
controls for the capabilities it introduces.
