# Global Payments AI demonstration

## Start or reset the isolated demo

```bash
./scripts/demo-payments.sh
```

This command uses the `decisionvault-payments-demo` Compose project, deletes
only that project's volumes, rebuilds it, and starts the presentation at
`http://127.0.0.1:3400`. It does not address or reset the normal development
Compose project.

Presenter login: `presenter@globalpayments.demo` / `DecisionVault!`

Restricted-user check: `analyst@globalpayments.demo` / `DecisionVault!`

All merchant, owner, transaction, fraud, chargeback, AML, sanctions, and outcome
records in this scenario are synthetic. No real person, merchant, account, or
payment transaction is represented.

## 7–8 minute presentation script

### Presenter mode

Open **Northstar Digital Commerce** and select **Presenter mode** in the decision
header. The guided strip keeps the presentation on a six-step path: Overview,
Evidence, AI Analysis, Decision Memory, Approvals, and Reports. Use **Next demo
moment** to advance, while retaining normal tab navigation if the audience asks
to explore.

The Overview now begins with **Why this matters to the business**, summarizing
the synthetic exposure, the activation control, and the accountable human
owner. Treat the figures as deterministic demo data, not predictive estimates.

### 0:00–0:45 — Frame the decision

1. Sign in as the presenter.
2. On **Dashboard**, select **Open Decision Center**.
3. Click **Northstar Digital Commerce LLC**.

Expected: a critical-risk merchant-acquiring Decision with 89% recorded
confidence, eight approved evidence records, and a human-owned question:
approve, conditionally approve, restrict, or reject.

Narration: “Northstar is growing quickly, but chargebacks, transaction behavior,
and incomplete ownership evidence conflict. DecisionVault does not make the
approval. It organizes what an accountable risk committee needs to decide.”

Transition: “First, let’s see how the source documents became governed,
reviewable knowledge.”

### 0:45–1:50 — AI moment 1: document intelligence

1. Click **Knowledge Cards** in the primary navigation.
2. Point to the eight cards and the banner **Deterministic synthetic extraction**.
3. Expand the story verbally while scrolling through merchant profile, KYB,
   fraud, the critical 24-hour network alert, chargeback, AML, sanctions, and
   policy cards.

Expected: each card shows structured facts, synthetic-file provenance,
authority, published state, trust, and AI retrieval eligibility.

Narration: “For presentation reliability these extractions are deterministic and
pre-seeded, but they use the same governed Knowledge Card boundary as ingestion.
Every fact remains reviewable, attributable, and human-published.”

Transition: use the browser Back action, then click **Evidence**.

### 1:50–3:00 — AI moment 2: governed evidence picture

1. Click **Evidence**.
2. Pause on **Critical signal detected**, then point to **Important facts**,
   **Conflicting evidence**, **Material risks**, and **Missing information**.
3. Expand **Trace finding to source** to show the signal → source → extracted
   fact → governing policy → proposed control chain.
4. Scroll into **Active decision evidence** and point to relationship, trust,
   immutable snapshot, and selection rationale.

Expected highlights:

- Chargebacks rose 0.62% → 1.48%; 58% are fraud-coded.
- A 24-hour network alert detected an active coordinated card-testing attack,
  11.6× baseline attempts, and $186,000 in attempted exposure.
- Card testing is 3.9× baseline and device sharing is 14.7%.
- The merchant says there is no material anomaly.
- A 25% owner is unresolved.
- Verified parties screen clear, but final sanctions disposition is incomplete.

Narration: “The system has isolated a critical signal rather than burying it in
the file set. This is deterministic governed analysis—not a black-box risk
score. The alert remains tied to its source, and an accountable human still
decides what happens next.”

Transition: click **AI Analysis**.

### 3:00–4:15 — AI moment 3: grounded recommendation

1. Click **AI Analysis**.
2. Read the recommendation: **Do not activate processing while the critical
   fraud alert remains open. Consider conditional approval only after independent
   containment verification and required controls.**
3. Point to Facts, Assumptions, Risks, Missing information, Proposed controls,
   and numbered Citations.
4. Compare **Current evidence** with **If the critical controls are verified**.
   Explain that this is a deterministic scenario, not a forecast or approval.
5. Use **Continue to governed approval** to demonstrate where AI stops and
   accountable human action begins.

Expected controls: 10% reserve, $5M cap, corridor restrictions, enhanced
monitoring, 30-day UBO/expected-activity remediation, and human committee
approval.

Narration: “AI can retrieve, summarize, identify gaps, compare, and draft an
explanation. It cannot silently approve Northstar. Notice that merchant-supplied
volume remains an assumption, incomplete AML evidence is not called suspicious
activity, and every proposed control traces to governed evidence.”

Optional live enhancement: open **Ask DecisionVault** and choose one of the
preset executive questions—for example, “Why should Northstar not be activated
today?” or “What would change the recommendation?” Presets run immediately and
reduce typing during the presentation. Identify the output using its on-screen
mode label. Skip this click if timing or Ollama availability
is uncertain; the core recommendation does not depend on it.

Transition: return to Northstar and click **Decision Memory**.

### 4:15–5:45 — AI moment 4: Decision Memory

1. Click **Decision Memory**.
2. Point to the disclaimer that structural similarity is not a recommendation.
3. Select **Compare** for **Vela Digital Media**, then for **Orbit Tickets Online**.
4. Call out successful, failed, rejected, and restricted historical outcomes.

Expected:

- Vela succeeded under reserve and volume controls.
- Orbit failed after chargebacks reached 2.3%.
- Meridian was appropriately rejected for UBO/AML contradictions.
- Atlas is misleading because account takeover differs from card testing.
- Scores remain `decision_similarity_v1`; observed usage does not affect rank.

Narration: “Decision Memory retrieves authorized historical records before it
ranks them. It explains shared and different characteristics and includes both
success and failure—without turning similarity into approval.”

Authorization proof, rehearsed before the presentation: sign in as the analyst.
CipherPay does not appear in Decision Center, counts, Memory candidates, or
direct lookup. Do not spend presentation time switching accounts unless asked.

Transition: stay in Decision Memory and move to the governed-reference and
lesson sections.

### 5:45–6:50 — AI moment 5: Decision Learning

1. In **Governed precedent record**, show the attached historical cases.
2. Point to **Observed usefulness** values: highly useful, useful, misleading,
   and harmful.
3. In **Governed lesson choices**, show beneficial, neutral, ineffective, and
   appropriate-rejection results.

Expected: every row is labeled as an observed, pre-seeded historical evaluation
with rationale. Correction controls require a human rationale.

Narration: “The organization records what happened after a precedent or lesson
was used. AI cannot certify usefulness. These are governed human evaluations,
and observed usefulness supports reuse consideration—it does not prove universal
applicability.”

Transition: click **Approvals**.

### 6:50–7:40 — Human accountability close

1. Click **Approvals**.
2. Do not submit a final approval action.
3. Point to reviewer assignment, rationale, findings, conditions, and auditable
   human actions.

Narration: “DecisionVault’s AI value is visible across extraction, evidence
assembly, explanation, memory, and learning. But the final choice—approve,
conditionally approve, restrict, or reject—remains an explicit accountable human
act with evidence and rationale preserved.”

Close: “That is governed Decision Intelligence: faster understanding without
giving up provenance, access control, or human responsibility.”

## Presentation truth labels

- **Deterministic synthetic extraction:** pre-seeded structured cards for the
  eight synthetic source documents.
- **Deterministic governed analysis:** pre-seeded evidence categories,
  recommendation, controls, and citations.
- **Pre-seeded historical record:** historical Decisions, outcomes, precedent
  evaluations, and lesson evaluations.
- **Live local AI / deterministic fallback:** only the optional Ask experience;
  it cannot mutate approval, adoption, learning, or publication state.
