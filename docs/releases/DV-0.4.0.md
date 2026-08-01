# DecisionVault 0.4.0 — Electronic Manufacturer Decision Center

This release introduces supplier qualification decisions tailored to electronic manufacturers.

## Included
- Supplier name, location, owner, due date, priority, risk, type, and business unit.
- Transparent readiness scoring from approved, trusted, governed evidence.
- Electronics-specific evidence covering quality certification, SMT/PCB capability, ESD controls, traceability, counterfeit prevention, supply continuity, and cybersecurity.
- Human-readable evidence gaps and accountable review guidance.
- Decision status updates with audit events.

## Readiness formula
- Approved evidence: 40 points
- Trusted evidence: 30 points
- Evidence coverage: up to 20 points
- Governed AI eligibility: 10 points

The score supports human review; it does not approve or reject suppliers.

## Database
Schema changes require a fresh pre-production database deployment.
