# Product vision

DecisionVault helps organizations make faster, smarter, and more confident decisions with knowledge they can trust.

The product does not replace a customer's authoritative document repositories. It connects source information to governed Knowledge Cards, evidence, approvals, retrieval, and Decision Cases:

```text
Source information → ingestion → draft Knowledge Card → human review
                   → published knowledge → decision intelligence
```

## Product principles

- Governed knowledge, not raw documents, is the canonical user-facing object.
- Answers and recommendations remain grounded in retained, citable evidence.
- Human review and approval establish authority; AI assistance does not replace governance.
- Tenant isolation, classification, access policy, and auditability precede retrieval, ranking, or AI use.
- Existing repositories remain authoritative while DecisionVault adds decision context and traceability.
- The system should degrade safely when optional Ollama capabilities are unavailable.

## Current scope

The repository currently includes tenant and organization foundations, authentication and revocable sessions, workspaces, source ingestion, governed Knowledge Cards, hybrid retrieval, grounded Q&A, Decision Cases with evidence, dashboard views, and audit timelines. This is a pre-release product; shipped behavior and accepted decisions, rather than this vision, define the current contract.

