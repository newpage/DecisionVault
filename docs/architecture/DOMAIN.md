# DecisionVault domain foundation

## Primary ownership chain

```text
Tenant
  └── Organization
      └── Workspace
          ├── Source Documents
          ├── Knowledge Cards
          └── Decision Cases
```

## Knowledge model

A **Knowledge Card** is the governed, user-facing knowledge object. A document is evidence or a source—not the canonical knowledge object.

Knowledge Cards have lifecycle, authority, classification, applicability, evidence, review status, and AI-usage eligibility.

## Security rule

Authorization and tenant filtering occur before retrieval, ranking, or AI processing.
