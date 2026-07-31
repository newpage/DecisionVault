# ADR-0001: Pre-release breaking changes

## Status
Accepted

## Decision
Until explicitly changed, every DecisionVault release starts with a fresh database. The project provides no schema, API, or implementation backward compatibility.

## Consequences
- No upgrade migrations or compatibility shims.
- Schemas and APIs may be redesigned freely.
- Demo data is reseeded on every fresh start.
- Architecture quality and delivery speed take priority over preserving pre-release behavior.
