# DecisionOS — Project Details (Single Source of Truth)

> **Read this file first.** Every human and AI coding agent working in this repository must treat this document as the product and architecture source of truth. If a task conflicts with this document, **flag the conflict; do not silently pick an interpretation.** (See Section 25 for conflicts already identified.)

- **Project:** DecisionOS
- **Tagline:** AI decision engine for pharma supply-chain operations
- **Context:** Hackathon MVP. Correctness, demo reliability, and a clear architecture beat breadth.
- **Core pipeline:** `ANALYZE → SIMULATE → DECIDE → VERIFY`
- **Output of every decision:** Recommendation + Expected impact + Evidence + Verification status + Audit trail

---

## Table of Contents

1. What We Are Building (and Not)
2. Core Philosophy
3. Product Evolution: Question-Driven → Autonomous
4. End-to-End Workflow
5. Data Sources: External vs Synthetic
6. Normalization Layer
7. Data Model
8. Autonomous Decision Detection
9. ANALYZE
10. SIMULATE
11. DECIDE
12. VERIFY (Core Differentiator)
13. Deterministic Numerical Engine
14. Supplier Intelligence
15. Evidence and Audit Trail
16. Human Control
17. Frontend
18. API Surface
19. Architecture and Repository Layout
20. Failure Behavior
21. Security and Secrets
22. Testing
23. Evaluation
24. MVP Scope, Priorities, and Build Order
25. Known Conflicts and Open Decisions
26. Do-Not-Build List
27. Demo Scenario
28. Agent Rules
29. First Task for the Coding Agent
30. Glossary

---

## 1. What We Are Building (and Not)

### We are building
A system that **continuously analyzes a pharma business's operational data plus external signals**, **autonomously detects situations that need an operational decision**, and for each one produces:

1. A **recommended action** (selected from quantified alternatives),
2. The **expected impact** (computed by deterministic code),
3. The **evidence** used,
4. A **verification result** (an independent recomputation of the critical numbers),
5. A full **audit trail**,

and then hands it to a **human for approval**.

Business data tells you *what happened*. DecisionOS determines *what to do, why, what else was considered, what it will change, and whether the key numbers can be independently verified.*

### We are NOT building
- A "chat with your data" product
- A generic AI chatbot
- A generic analytics dashboard
- A CRUD application
- A system that executes consequential actions on its own

---

## 2. Core Philosophy

AI should not merely explain data. AI should help determine action. But consequential AI decisions must be:

- **Evidence-based** — every important claim points to a data record
- **Simulation-backed** — actions are compared by computed outcomes
- **Numerically grounded** — numbers come from deterministic code, never from an LLM
- **Independently verified** — a separate path recomputes the critical numbers
- **Traceable** — complete audit trail
- **Human-controlled** — humans approve consequential actions

**The differentiator is not "we use an LLM."** It is:

```
REASONING
  + DETERMINISTIC DECISION LAYER
  + INDEPENDENT VERIFICATION
  + EXTERNAL BUSINESS CONTEXT
  + AUDITABILITY
```

---

## 3. Product Evolution: Question-Driven → Autonomous

**Original submission (still valid conceptually):** a user asks a natural-language question such as *"Which inventory should we act on this month to minimize expiry losses without causing stockouts?"* The system runs ANALYZE → SIMULATE → DECIDE → VERIFY and returns the output.

**Current direction (primary):** the owner should not have to keep asking. DecisionOS ingests data continuously, scans the business state, and **discovers decisions itself**. It effectively asks itself: *"What operational decisions currently require attention?"* and then investigates them. The owner sees **decisions and risks**, not raw data.

**"Autonomous" means** autonomous *analysis, detection, simulation, and recommendation*. It does **not** mean autonomous execution. Human approval is the final control for consequential actions.

**Question mode** (manual/debug mode): optional. Implement only after the autonomous pipeline works. A question is translated into a decision candidate (scope: medicine/location/goal) and enters the *same* pipeline. It must never become a separate code path with different guarantees.

---

## 4. End-to-End Workflow

```
 ┌────────────────────┐   ┌──────────────────────┐
 │ Client PostgreSQL  │   │ External public data │
 │ (synthetic demo)   │   │ WHO·Open-Meteo·CDSCO │
 └─────────┬──────────┘   │ ·NPPA                │
           │              └──────────┬───────────┘
           ▼                         ▼
     ┌─────────────────────────────────────┐
     │ 1. DATA INGESTION                   │
     └──────────────────┬──────────────────┘
                        ▼
     ┌─────────────────────────────────────┐
     │ 2. DATA NORMALIZATION               │
     └──────────────────┬──────────────────┘
                        ▼
     ┌─────────────────────────────────────┐
     │ 3. EXTERNAL ENRICHMENT              │
     └──────────────────┬──────────────────┘
                        ▼
     ┌─────────────────────────────────────┐
     │ 4. RISK / OPPORTUNITY DETECTION     │
     └──────────────────┬──────────────────┘
                        ▼
     ┌─────────────────────────────────────┐
     │ 5. DECISION CANDIDATE GENERATION    │
     └──────────────────┬──────────────────┘
                        ▼
     ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐
     │ ANALYZE  │→│ SIMULATE │→│ DECIDE │→│ VERIFY │
     └──────────┘ └──────────┘ └────────┘ └───┬────┘
                                              ▼
                                  ┌───────────────────────┐
                                  │ DECISION PACKAGE      │
                                  │ VERIFIED or WITHHELD  │
                                  └──────────┬────────────┘
                                             ▼
                                  ┌───────────────────────┐
                                  │ HUMAN REVIEW/APPROVAL │
                                  └───────────────────────┘
```

| Stage | Responsibility | Primary technology |
|---|---|---|
| Ingestion | Read client DB; pull/refresh external data; record freshness | SQL, HTTP clients |
| Normalization | Map names (medicines, diseases, suppliers, manufacturers, locations, batches) to canonical forms | Deterministic rules first, LLM-assist second |
| Enrichment | Attach disease, weather, regulatory, pricing signals to client entities | Python services |
| Detection | Scan state, flag situations needing a decision | Deterministic rules (MVP) |
| Candidate generation | Create `decision_candidates` with trigger, priority, evidence | Deterministic |
| ANALYZE | Explain what/why/evidence/constraints | Structured evidence + LLM reasoning |
| SIMULATE | Generate candidate actions, compute outcomes | Deterministic Python |
| DECIDE | Choose action from quantified trade-offs | Deterministic scoring; LLM explains |
| VERIFY | Independently recompute critical numbers; release or withhold | Separate deterministic module |
| Package | Assemble recommendation, impact, evidence, verification, audit | Python |
| Human review | Approve / reject | UI + API |

---

## 5. Data Sources: External vs Synthetic

**Rule:** the UI, API, and docs must always make clear which data is **REAL EXTERNAL** and which is **SYNTHETIC CLIENT DEMO DATA**. Never claim synthetic data is real customer data. Every record carries a `data_origin` of `SYNTHETIC_CLIENT` or `EXTERNAL_<SOURCE>`.

### 5.1 Synthetic client data (we generate it)
We do not have a real pharma company's private data. Generate realistic synthetic data for: medicines, inventory batches, locations, demand history, disease concentration signals, seasonal factors, suppliers, supplier transactions, supplier quality events, costs, lead times, thresholds, procurement constraints. Use a fixed random seed so demos are reproducible. Plant specific scenarios (see Section 27), including one exact batch collision with a real CDSCO NSQ record (or a clearly labelled planted record if no real match is practical).

### 5.2 External sources

| Source | Purpose | Credentials | Notes |
|---|---|---|---|
| **WHO ICD API** | Disease terminology / classification / normalization | `WHO_CLIENT_ID`, `WHO_CLIENT_SECRET` (already held; `.env` only) | **Not** a regional disease prevalence database. Used only to normalize/classify disease names. |
| **Open-Meteo** | Historical + forecast weather (temperature, precipitation, etc.) | None for basic usage | Evidence signal only; see 5.3. |
| **CDSCO** | NSQ (Not of Standard Quality) drug alerts | **No API key. Do not look for one.** | Official website publishes structured NSQ info. Ingest and normalize. |
| **NPPA** | Medicine pricing / reference price | **No API key** for MVP | **Reference signal only**; not a supplier quotation. |

Ingestion details for CDSCO/NPPA (scrape vs. downloaded files vs. manual snapshot) are an implementation decision; prefer the most reliable approach for demo day, **cache raw snapshots**, and record `source_url` and `ingested_at`. Never fabricate records if retrieval fails.

### 5.3 Rules for each external signal

**WHO ICD**
- Maps client disease strings (e.g., "Respiratory infection") to standardized terminology.
- Cache results; ICD lookups should not be on the hot path of every scan.
- Not a prevalence source. Disease *concentration* signals in the demo come from the (synthetic) client `disease_data` table.

**Open-Meteo**
- Do **not** hard-code `rain ⇒ demand +20%`.
- Weather contributes to a demand adjustment **only when relevant to the disease/medicine context** (via a configurable `disease_weather_relevance` mapping, explicitly labelled as an assumption/config).
- Forecast demand signal = f(historical demand, seasonality, disease concentration, weather signal). See Section 9.

**CDSCO**
- Match at **batch level**: normalized product name + batch number (+ manufacturer where available).
- Exact batch match with client inventory → high-priority quality decision candidate.
- Same product but different batch → **do NOT** claim client inventory is affected. At most a low-priority informational note.
- No match → no claim.

**NPPA**
- Reference/ceiling price context for cost anomaly checks.
- The client's actual procurement price (from `supplier_transactions`) is the real cost. Never conflate the two.

---

## 6. Normalization Layer

Client and external sources name things differently:

```
Client:  "Para 500"
WHO:     "Paracetamol"
CDSCO:   "Paracetamol Tablets IP 500 mg"
```

Do **not** rely on exact string matching. Normalize: medicine names, disease names, manufacturer names, supplier names, locations, batch numbers.

**Matching policy (in order):**
1. **Deterministic first:** canonicalization (case, whitespace, punctuation, dosage-form tokens like "Tablets IP", unit formats like "500 mg"), curated alias table, exact/near-exact rules, token-set comparison with high threshold.
2. **LLM-assisted second:** for ambiguous candidates only; output is a *proposed* mapping with a confidence and rationale, stored in a mapping table.
3. **Critical decisions must not depend solely on an LLM fuzzy match.** A CDSCO batch alert must be backed by a deterministic match on batch number plus a high-confidence product match. LLM-only matches are stored as `PROPOSED` and are **not** allowed to create CRITICAL candidates without deterministic corroboration (or human confirmation).
4. Store every mapping in `entity_mappings` with `method` (`DETERMINISTIC | LLM_ASSISTED | MANUAL`), `confidence`, and timestamps.

Batch numbers: normalize only whitespace/case; keep otherwise exact. Never fuzzy-match batch numbers.

---

## 7. Data Model

Concepts below are mandatory; exact columns may be refined during implementation (record refinements in the migration files and update this section). Use `NUMERIC`/`Decimal` for money and quantities where fractional values matter. Use `NULL` for unknown values — **never treat missing as zero.**

### 7.1 Client operational tables (synthetic)

**medicines**
`id, name, normalized_name, disease_category, therapeutic_category, unit_cost, shelf_life_days?, data_origin`

**locations**
`id, name, region, latitude, longitude` (lat/lng needed for Open-Meteo)

**inventory_batches**
`id, medicine_id, batch_number, location_id, quantity, expiry_date, unit_cost, supplier_id?/manufacturer, data_origin`

**demand_history**
`id, medicine_id, location_id, period_date (day or month), quantity_demanded, data_origin`

**disease_data**
`id, location_id/region, disease, normalized_disease, icd_code?, concentration_signal, period_date, source, data_origin`

**seasonal_factors**
`id, disease, region?, period (month), multiplier, source, data_origin`

**suppliers**
`id, name, normalized_name, location`

**supplier_offers** (current quotes/availability)
`id, supplier_id, medicine_id, quoted_price, available_quantity, lead_time_days, quoted_at, regulatory_notes?`

**supplier_transactions** (client procurement history)
`id, supplier_id, medicine_id, quantity, purchase_price, order_date, expected_delivery_date, actual_delivery_date`

**supplier_quality_events**
`id, supplier_id, medicine_id, batch_number, issue, rejected_quantity, event_date, source`

**inventory_policies** (constraints)
`medicine_id, location_id, safety_stock, stockout_threshold, min_order_qty, max_order_qty, redistribution_cost_per_unit, holding_cost_per_unit_day?, stockout_penalty_per_unit`

### 7.2 External-data tables

**cdsco_alerts**
`id, product_name, normalized_product_name, batch_number, manufactured_by, manufacturing_date, expiry_date, nsq_result, reporting_source, reporting_lab_state, reporting_month, source_url, ingested_at`

**nppa_prices**
`id, medicine_name, normalized_name, formulation, reference_price, effective_date, source_url, ingested_at`

**weather_observations / weather_forecasts**
`id, location_id, date, variables(JSON/columns), source_request_timestamp, fetched_at`

**external_fetch_log**
`id, source, status, fetched_at, record_count, error?` — powers data-freshness display.

### 7.3 Normalization

**entity_mappings**
`id, entity_type, source_system, source_value, canonical_value, method, confidence, status(CONFIRMED|PROPOSED|REJECTED), created_at`

### 7.4 Decision tables

**decision_candidates**
`id, trigger_type, priority, priority_score, medicine_id, location_id, evidence_refs(JSON), detected_at, status(DETECTED|ANALYZING|COMPLETE|INSUFFICIENT_EVIDENCE|DISMISSED)`

**decisions**
`id, candidate_id, analysis(JSON), candidate_actions(JSON), simulation_results(JSON), selected_action(JSON), expected_impact(JSON), verification(JSON), verification_status(VERIFIED|WITHHELD|INSUFFICIENT_EVIDENCE|PENDING), approval_status(PENDING|APPROVED|REJECTED|NOT_APPLICABLE), evidence(JSON), audit(JSON), created_at, updated_at`

**audit_events** (append-only)
`id, decision_id, stage, event_type, payload(JSON), actor(SYSTEM|LLM:<model>|HUMAN:<id>), created_at`

---

## 8. Autonomous Decision Detection

A scheduler (simple in-process periodic job or a manual "Run scan" endpoint — no heavy infrastructure) runs a scan over current state and produces `decision_candidates`.

### 8.1 Trigger types

| # | Trigger | Example condition (rule-based, MVP) |
|---|---|---|
| 1 | Expiry risk | Projected consumption before expiry < on-hand for a batch |
| 2 | Stockout risk | Projected coverage days < lead time (+ safety) |
| 3 | Excess inventory | Coverage far above target horizon |
| 4 | Demand surge | Forecast demand ≫ trailing baseline |
| 5 | Demand decline | Forecast demand ≪ trailing baseline |
| 6 | Disease-driven demand change | Disease concentration shifts for the medicine's disease category |
| 7 | Weather-driven relevant signal | Weather signal relevant to the disease context |
| 8 | Supplier reliability deterioration | Rolling on-time/quality metrics trend down (needs history) |
| 9 | Quality / regulatory alert | CDSCO NSQ **exact batch** match |
| 10 | Procurement opportunity | Cheaper qualified supplier or NPPA-referenced anomaly |
| 11 | Cost anomaly | Purchase price deviates materially from history/reference |
| 12 | Inventory imbalance between locations | One location in surplus/expiry risk while another in stockout risk |

Thresholds live in a config file (e.g., `core/config/detection_rules.yaml`), not scattered in code.

### 8.2 Prioritization (MVP: deterministic)
`priority_score` = weighted combination of: estimated financial impact, stockout risk, expiry risk, regulatory/quality severity, urgency (days to expiry / lead time), data confidence, affected quantity. Map to `CRITICAL | HIGH | MEDIUM | LOW` via thresholds. Do not build an elaborate ranking system. Quality alerts with exact batch matches are `CRITICAL` by rule.

### 8.3 Deduplication
A candidate for the same `(trigger_type, medicine, location)` that is already open is **updated**, not duplicated.

---

## 9. ANALYZE

Answers: **What is happening? Why? What evidence supports it? What constraints exist?**

### 9.1 Deterministic evidence assembly (no LLM)
For a candidate, gather a structured **evidence bundle**: inventory batches (qty, expiry), demand trend, seasonal factor, disease signal, weather signal, supplier lead times/offers, constraints/policies, regulatory alerts, reference prices. Each item carries a `source_ref` (table + id, or external request ID + timestamp) and `data_origin`.

### 9.2 Demand signal (deterministic)
```
baseline          = trailing average demand (window configurable)
seasonal_adj      = seasonal multiplier for (disease, period)
disease_adj       = f(disease concentration signal vs. baseline)
weather_adj       = f(weather signal) — applied ONLY if relevant per disease_weather_relevance
forecast_demand   = baseline × seasonal_adj × disease_adj × weather_adj
```
- Adjustments are bounded (configurable clamp) to prevent runaway forecasts.
- Each adjustment is recorded with its inputs so it can be shown and re-derived.
- If an input is missing (e.g., Open-Meteo down), that factor is **omitted and flagged** — not set to 0 and not silently set to 1 without a note. Record `signals_missing` in the analysis.
- Forecast uncertainty (e.g., std of historical residuals) is computed deterministically and used by stockout probability.

### 9.3 LLM reasoning (structured)
The LLM receives the evidence bundle (not raw database access) and returns **structured JSON**:
- `drivers[]` — key drivers, each with `evidence_refs[]`
- `root_cause_explanation`
- `constraints[]`
- `candidate_actions[]` — proposed action *types* with parameters (e.g., redistribute X units from A to B)
- `confidence_notes`

Rules:
- The LLM must **not invent data** or numbers not present in the bundle.
- Every important claim must reference evidence IDs. Post-validate: any `evidence_ref` not in the bundle ⇒ discard that claim and log it.
- LLM-proposed actions are *proposals*; the simulator validates feasibility (quantities available, constraints) and may reject or clamp them.
- Deterministic fallback: a rule-based action generator (Section 10.1) always exists so the pipeline works if the LLM is down.

---

## 10. SIMULATE

### 10.1 Candidate actions
Always include **Do nothing** as the baseline. Others, as applicable:

- Prioritize FEFO (first-expiry-first-out) consumption
- Redistribute inventory between locations
- Reorder (from a specified supplier)
- Delay reorder
- Change supplier
- Split procurement across suppliers
- Move inventory between locations (redistribution)
- Consume expiring inventory first

### 10.2 Per-action outputs (all computed by deterministic code)
```
expiry_loss_value
expected_stockout_units / stockout_probability
stockout_cost (units × policy penalty)
procurement_cost
redistribution_cost
holding_cost (if modeled)
quality_risk_cost (if signals exist)
total_expected_cost
net_benefit_vs_baseline  (= baseline total cost − action total cost)
assumptions[]  (every assumption used, explicit)
inputs_snapshot (the exact rows/values used)
```

Example shape (values are **illustrative only**; real values must come from DB inputs):

| Action | Expiry loss | Stockout risk | Action cost |
|---|---|---|---|
| A: Do nothing | ₹4.8L | 8.2% | ₹0 |
| B: Redistribute | ₹1.7L | 4.1% | ₹35,000 |
| C: Reorder | ₹3.2L | 2.1% | ₹6.5L |

### 10.3 Core formulas (MVP definitions; keep documented in code and tests)
- **Expiry loss (per batch)** = `max(0, batch_qty − consumable_before_expiry) × unit_cost`, where `consumable_before_expiry` is determined by a FEFO consumption of forecast demand across batches in expiry order (batches expiring earlier are consumed first).
- **Stock coverage (days)** = `usable_stock / forecast_daily_demand` (usable = non-expired, non-quarantined).
- **Stockout probability** = P(demand over exposure window > available supply). MVP: normal approximation using `forecast_demand` and its std over the exposure window (lead time for reorder paths, or the planning horizon otherwise). Document the approximation. A Monte Carlo variant is optional; if used, use a fixed seed.
- **Procurement cost** = `qty × offer price` (+ any configured fees); uses the *client-specific* supplier price, not NPPA.
- **Redistribution cost** = `units × redistribution_cost_per_unit` (per policy), plus a feasibility check that the source location doesn't create a new stockout.
- **Quarantine (quality alert)**: units in the exact NSQ-matched batch are excluded from usable stock and valued as at-risk; the action set includes quarantine/return/replace.

All formulas operate on `Decimal`/integers where appropriate; rounding rules are defined once and shared as constants (but the verifier does **not** import simulator code — see Section 12).

### 10.4 Simulator purity
The simulator is a pure function: `(inputs_snapshot, action) → outcome`. No network, no LLM, no DB writes inside it. It receives an **inputs snapshot** (loaded once, serialized into the audit record) so results are reproducible.

---

## 11. DECIDE

The decision engine selects an action from **structured simulation results**, not from LLM opinion.

- **Objective (MVP):** minimize `total_expected_cost` subject to hard constraints:
  - stockout probability ≤ policy threshold,
  - no use of quarantined/NSQ-matched units,
  - quantity/MOQ/budget/lead-time feasibility,
  - supplier qualification rules (e.g., exclude suppliers with known quality failures above threshold; **UNKNOWN history is not "good" and not "bad" — it is flagged**).
- If no action satisfies hard constraints → `INSUFFICIENT_EVIDENCE` / `NO_FEASIBLE_ACTION` (do not force a pick).
- Tie-breaking and ranking rules are deterministic and documented.
- The **LLM then explains** the decision in natural language, constrained to the computed numbers (post-validated: any number in the explanation must be traceable to the simulation output; otherwise regenerate or fall back to a template explanation).
- Output: `selected_action`, `ranked_alternatives`, `rejection_reasons` per alternative, `expected_impact` (the claims that will be verified).

Forbidden: "Action B is best" with no computed support.

---

## 12. VERIFY (Core Differentiator)

**The AI/reasoning path must not grade its own homework.**

```
REASONING PATH                      VERIFICATION PATH
Analyze → Simulate → Decide         Read RAW inputs → Recompute independently
   │                                     │
   └── claim: savings = ₹8.21L           └── recomputed: ₹8.21L
                    └────────── COMPARE ──────────┘
                         MATCH → VERIFIED → release
                         MISMATCH → WITHHELD → do NOT release
```

### 12.1 Independence requirements
1. **Separate module** (`services/verification/`) that **does not import** simulation/decision code or shared formula helpers.
2. **Reads raw inputs itself** (from the database tables and the stored external-record IDs), not from the simulator's inputs snapshot or intermediate results. It may check that the snapshot matches current DB rows (detecting drift).
3. **Different computation method where practical** — e.g., simulator uses a vectorized/closed-form approach; verifier replays a **day-by-day ledger** of stock, FEFO consumption, and expiry. Same business definitions (documented in Section 10.3), independently implemented.
4. **No LLM in the verifier's numeric path.** (An LLM may be used elsewhere, e.g., to phrase a mismatch report, but never to compute or judge numbers.)

### 12.2 What gets verified (the "critical numerical claims")
- Expiry loss (baseline and selected action)
- Projected demand over the horizon
- Stock coverage
- Stockout probability / expected stockout units
- Procurement / redistribution cost
- Net benefit (savings) vs. baseline
- Quantities moved/ordered and their feasibility

### 12.3 Comparison
- Each claim has a **tolerance** defined in config (e.g., currency: ±₹1 absolute or tight relative; quantities: exact integer match; probabilities: small absolute epsilon). Tolerances must be tight and documented; do not widen them to make tests pass.
- Result per claim: `MATCH | MISMATCH` with both values.
- Aggregate: all claims MATCH → `VERIFIED`. Any MISMATCH → `WITHHELD`.

### 12.4 Hard rule
**On verification failure the recommendation is WITHHELD.** It must never be silently released, auto-corrected to the verifier's number and shown as verified, or downgraded to a warning. The UI shows the mismatch (AI value vs. verifier value) and the decision stays withheld. (Whether a WITHHELD decision may be re-run after fixing data is allowed; re-run creates a new audit record.)

### 12.5 Other verification outcomes
- `INSUFFICIENT_EVIDENCE` — required inputs missing/unknown; no recommendation released.
- `PENDING` — in progress.

---

## 13. Deterministic Numerical Engine

All important numbers are computed in Python deterministic code:

expiry loss, projected demand, stock coverage, stockout risk inputs, procurement cost, redistribution cost, supplier metrics, savings, inventory quantities.

| Component | Does | Does NOT |
|---|---|---|
| Deterministic code | All calculations, constraint checks, ranking | Interpret free text |
| LLM | Reasoning, evidence summarization, root-cause explanation, candidate-action proposals, natural-language explanation, ambiguous-name mapping proposals | Calculate, be the source of any number, be the verifier |

Provider strategy: OpenAI and Gemini API access exists. Wrap both behind a single `LLMClient` interface with structured-output (JSON schema) validation, timeouts, and retries. Choose which model does what by config. Do not build a multi-agent framework.

---

## 14. Supplier Intelligence

Goal: answer **"If we need to procure this medicine, where should we buy it from?"**

### 14.1 Factors
cost, quality, reliability, lead time, availability, historical delivery performance, historical quality performance, regulatory signals, procurement constraints.

### 14.2 Metrics (derived from the **client's own** procurement history)
- Average purchase price (and recent trend)
- On-time delivery rate = on-time deliveries / total deliveries (actual ≤ expected)
- Average actual lead time (and variance)
- Quality acceptance rate = 1 − rejected_qty / received_qty (from quality events)
- Sample size (`n_orders`) — always shown; small `n` lowers confidence

**Do not invent supplier quality scores.** Metrics are computed or UNKNOWN.

### 14.3 Illustrative example (the numbers below are *examples of the shape*, not real data)
| Supplier | Avg cost | On-time | Quality acceptance | Avg lead time |
|---|---|---|---|---|
| A | ₹82 | 96% | 99% | 4 d |
| B | ₹76 | 82% | 94% | 8 d |
| C | ₹89 | 98% | 99.5% | 3 d |

The cheapest (B) is **not automatically chosen**. Lower reliability/quality can raise stockout risk, delay risk, quality risk, and *expected* total cost. The simulator folds these into expected cost (e.g., delay probability → effective lead time → stockout exposure; rejection rate → effective received quantity and re-order cost).

### 14.4 Unknown suppliers
If a supplier has no history with this client, show:
```
Reliability:                  UNKNOWN
Quality history:              UNKNOWN
Historical client performance: NONE
```
Other evidence may still appear (quoted price, quoted lead time, public regulatory/quality alerts) with explicit **"limited evidence"** labelling. Unknown must never be converted to a default good/bad score. The decision engine may still consider the supplier but must (a) flag the uncertainty, and (b) apply a documented policy (e.g., exclude from sole-source for critical items, or allow only a capped split-order share). This is a trust feature — keep it visible in the UI.

### 14.5 Presenting suppliers
Show the trade-offs and why the selected option satisfies current constraints. Never label a supplier "best" without showing the evidence and constraints behind it.

---

## 15. Evidence and Audit Trail

The system must be able to answer:

- What internal data was used? (table + record IDs)
- What external information was used? (source, request timestamp, record IDs)
- What assumptions were used?
- What calculations were performed? (formula versions, inputs snapshot)
- What alternatives were considered, and why was the selected one chosen?
- What did the independent verifier compute?
- Was it verified?
- When was each step performed, and by whom/what (system, which LLM + model version, human)?

### Evidence chain example
```
Inventory:   inventory_batches#1842
Demand:      demand_history#883
Disease:     disease_data#421
Weather:     Open-Meteo request @ 2026-xx-xxTxx:xx:xxZ (request params stored)
Regulatory:  cdsco_alerts#57
Supplier:    supplier_transactions#219
      ↓
Simulation (inputs snapshot hash, formula version)
      ↓
Decision (selected action, ranked alternatives)
      ↓
Verification (raw inputs read, recomputed values, per-claim result)
      ↓
Human approval (if any)
```

Implementation notes:
- `audit_events` is **append-only**.
- Store a hash of the inputs snapshot to show what was used at decision time.
- Store LLM prompts/responses (with secrets scrubbed) or at least prompt version + response, for traceability.
- Every evidence item displays its origin badge (`SYNTHETIC CLIENT` vs `EXTERNAL: <source>`) and freshness.

---

## 16. Human Control

- Consequential actions (redistribute, reorder, change supplier, quarantine) require **human approval**. The system produces a recommendation and a decision package; it does **not** execute purchases or transfers.
- Approval states: `PENDING → APPROVED | REJECTED`. Approval/rejection (with optional comment) is an audit event.
- Only `VERIFIED` decisions can be approved. `WITHHELD` and `INSUFFICIENT_EVIDENCE` cannot.
- "Execution" in the MVP is out of scope; approving simply records the decision and may show a "would be executed" summary.
- No authentication in MVP: approvals are attributed to a placeholder demo user.

---

## 17. Frontend

The frontend must feel like an **operational decision-control system** — not a chatbot, not a generic analytics dashboard.

### 17.1 Main dashboard
```
DecisionOS
AI Decision Engine for Pharma Operations

● SYSTEM ACTIVE      Last scan: <time>      Data freshness: <per source>

TODAY'S DECISION SIGNALS
[ Critical decisions: N ]  [ Emerging risks: N ]  [ Verified decisions: N ]

Decision cards (sorted by priority) ...
```

### 17.2 Decision card (shape)
```
CRITICAL DECISION
<Medicine> — <Location>

Expiry exposure: ₹X          Demand trend: +X%
Disease signal: HIGH         Stockout probability: X%

RECOMMENDED ACTION
<Action summary, e.g., Redistribute N units A → B>

Expected impact:
  Expiry loss avoided: ₹X
  Stockout risk: X% → Y%

✓ Independently Verified      (or ✕ WITHHELD — verification mismatch)

[ Evidence ]  [ Simulation ]  [ Audit Trail ]  [ Approve / Reject ]
```
All values are rendered from API data. Nothing in the UI is hard-coded demo numbers except the labelled synthetic dataset itself.

### 17.3 Decision detail view
Tabs/sections: **Analysis** (drivers + evidence), **Simulation** (all candidate actions side by side, with baseline), **Decision** (selected action, why, rejected alternatives), **Verification** (per-claim AI value vs verifier value, status), **Audit trail** (timeline), **Data provenance** (origin badges, freshness).

### 17.4 Procurement view (when procurement is part of the decision)
Medicine, required quantity, supplier comparison table (cost, quality, reliability, lead time, evidence/sample size, UNKNOWN badges), the decision rationale, and the evidence. Show trade-offs; do not present an unsupported supplier as objectively best.

### 17.5 States to design for
Empty (no decisions), loading, WITHHELD, INSUFFICIENT_EVIDENCE, external source unavailable (stale-data banner), LLM unavailable (deterministic-only banner).

### 17.6 Frontend scope guard
Next.js + React. Few screens: Dashboard, Decision detail, (Procurement section inside detail), optional Question mode, optional Data status page. No CRUD admin screens.

---

## 18. API Surface

FastAPI. JSON. Suggested endpoints (names may be refined; keep REST-ish and minimal):

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| POST | `/api/scan` | Run detection scan (manual trigger) |
| GET | `/api/candidates` | List decision candidates |
| POST | `/api/candidates/{id}/run` | Run ANALYZE→SIMULATE→DECIDE→VERIFY for a candidate |
| GET | `/api/decisions` | List decisions (filter by status/priority) |
| GET | `/api/decisions/{id}` | Full decision package |
| GET | `/api/decisions/{id}/evidence` | Evidence items with provenance |
| GET | `/api/decisions/{id}/simulation` | All candidate actions & outcomes |
| GET | `/api/decisions/{id}/verification` | Per-claim verification results |
| GET | `/api/decisions/{id}/audit` | Audit events |
| POST | `/api/decisions/{id}/approve` | Approve (only if VERIFIED) |
| POST | `/api/decisions/{id}/reject` | Reject |
| GET | `/api/data-status` | Source freshness, last fetch status |
| POST | `/api/ingest/{source}` | Trigger refresh for `who|open_meteo|cdsco|nppa` |
| GET | `/api/suppliers/compare?medicine_id=` | Supplier comparison with UNKNOWN handling |
| POST | `/api/query` | *(optional, later)* Question mode → creates candidate |

Rules: never return secrets; responses include `data_origin` and freshness where relevant; a `WITHHELD` decision's package must not present the selected action as a released recommendation.

### Credentials required (summary)
| Integration | Credentials |
|---|---|
| PostgreSQL | `DATABASE_URL` |
| OpenAI | `OPENAI_API_KEY` |
| Gemini | `GEMINI_API_KEY` |
| WHO ICD | `WHO_CLIENT_ID`, `WHO_CLIENT_SECRET` |
| Open-Meteo | none |
| CDSCO | none |
| NPPA | none |

---

## 19. Architecture and Repository Layout

```
Next.js (frontend)
    ↓ HTTP/JSON
FastAPI
    ↓
Decision Orchestrator
    ├── Data Layer (repositories, PostgreSQL)
    ├── External Enrichment (WHO, Open-Meteo, CDSCO, NPPA)
    ├── Detection
    ├── Analysis (evidence assembly + LLM reasoning)
    ├── Simulation Engine (pure, deterministic)
    ├── Decision Engine (deterministic selection + LLM explanation)
    ├── Verification Engine (independent, deterministic)
    └── Evidence / Audit
```

Suggested layout (adapt to the existing repo; see Section 29):

```
backend/
  app/
    main.py
    api/                 # routers
    models/              # SQLAlchemy models
    schemas/             # Pydantic schemas
    repositories/        # DB access
    core/                # config, logging, constants, LLM client interface
    integrations/
      who/
      open_meteo/
      cdsco/
      nppa/
    services/
      ingestion/
      normalization/
      enrichment/
      detection/
      analysis/
      simulation/
      decision/
      verification/      # MUST NOT import from simulation/ or decision/
      evidence/
    tests/
  scripts/
    seed_synthetic_data.py
frontend/
  (Next.js app)
project_details.md
.env.example
.gitignore            # must include .env
```

Principles: clean but not over-engineered. Each integration is modular so one failing source doesn't take down the system. No microservices, Kafka, Redis, Kubernetes, or complex agent frameworks unless there is a demonstrated real requirement. Database migrations via Alembic (or equivalent) — keep minimal.

---

## 20. Failure Behavior

The system must **fail safely** and never invent missing information.

| Failure | Required behavior |
|---|---|
| External API unavailable | Use cached/latest valid data where possible; show data freshness/staleness |
| WHO unavailable | Fall back to cached ICD mappings / curated alias table for disease normalization |
| Open-Meteo unavailable | Use stored historical weather/client signals; flag weather factor missing/stale |
| CDSCO unavailable | **Do not fabricate alerts.** Show "external regulatory data unavailable" + last successful fetch time |
| NPPA unavailable | Skip reference-price checks; flag |
| LLM unavailable | Deterministic detection, simulation, decision, and verification still work; analysis uses template/rule-based explanation; UI shows reduced-intelligence banner |
| LLM returns invalid/unsupported output | Discard unsupported claims, retry with limits, fall back to deterministic template |
| Verification mismatch | **WITHHOLD** recommendation |
| Insufficient evidence | Mark `INSUFFICIENT_EVIDENCE`; no recommendation |
| Unknown supplier history | Mark reliability/quality `UNKNOWN`; never default |
| Missing numeric input | Treated as **missing**, never as 0 |
| No batch match for CDSCO | Do not claim the client is affected |

---

## 21. Security and Secrets

- Secrets only in `.env`. Commit `.env.example` with placeholder names; `.gitignore` includes `.env`.
- Never hardcode, log, or return credentials in API responses/UI. Scrub secrets from audit-stored prompts and error traces.
- WHO credentials stay server-side; WHO tokens are obtained by the backend only.
- Authentication/authorization is **out of scope** for MVP (no signup, login, JWT, RBAC, password reset, SSO). Note this clearly in README: demo is single-tenant and unauthenticated.
- Validate and parameterize all DB access; validate LLM JSON outputs with schemas.

Example `.env.example`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/decisionos
OPENAI_API_KEY=
GEMINI_API_KEY=
WHO_CLIENT_ID=
WHO_CLIENT_SECRET=
```

---

## 22. Testing

Testing matters because the product claims reliability. Use `pytest`. Minimum coverage:

1. Inventory calculations
2. Expiry calculations (including multi-batch FEFO)
3. Stockout calculations
4. Supplier metrics (including small-sample and unknown-history cases)
5. Simulation calculations (every action type)
6. Verification calculations (independent implementation agrees with simulator on golden cases)
7. CDSCO batch matching (exact match, same-product-different-batch, no match, name-variant matching)
8. Disease normalization (including WHO-unavailable fallback)
9. Failure/mismatch behavior
10. Decision withholding behavior

**Critical test (must exist):**
```
Given AI/simulator result != verifier result
Expect decision.verification_status == WITHHELD
Never VERIFIED
And: approve endpoint rejects it
```

Additional tests: missing data is not treated as zero; UNKNOWN supplier is not scored; verifier module has no imports from simulation/decision (enforce with an import-lint test); LLM-disabled pipeline still produces a verified deterministic decision; golden-file tests with fixed seed synthetic data.

Mock external APIs in tests; keep a small set of recorded fixtures.

---

## 23. Evaluation

Dimensions (from the original submission):

- Decision accuracy
- Numerical accuracy
- Verification accuracy
- Unsupported recommendations
- Median latency
- P95 latency

The original plan references a benchmark of **100+ labeled scenarios**.

**Do NOT fabricate benchmark numbers.**

```
Benchmark status: TO BE RUN
```

When real measurements exist, report the actual numbers with the dataset/scenario version and date. Until then, any README/UI/pitch text must say "TO BE RUN" rather than stating a figure.

Suggested approach: a scenario generator that produces labeled cases (including injected AI-number errors to measure verification accuracy and planted unsupported claims to measure the unsupported-recommendation rate), plus a script that records latency per pipeline run.

---

## 24. MVP Scope, Priorities, and Build Order

### Priorities
1. Working autonomous decision pipeline
2. Deterministic simulation
3. Independent verification
4. Strong operational UI
5. External enrichment
6. Supplier intelligence
7. Tests
8. Deployment and documentation

**One polished end-to-end decision is worth more than ten unfinished features.**

### Suggested build order
1. **Foundation:** repo inspection, DB schema, synthetic seed script, `.env`, health endpoint.
2. **Deterministic core:** inventory/expiry/demand/stockout formulas + tests.
3. **Simulation engine** (baseline + FEFO + redistribute + reorder) + tests.
4. **Verifier** (independent ledger-replay) + tests, including mismatch→WITHHELD.
5. **Decision engine** (constraint filter + cost minimization).
6. **Detection scan** (expiry, stockout, imbalance first) → candidates.
7. **Orchestrator + decision package + audit events** end-to-end via API.
8. **Frontend:** dashboard + decision detail (simulation, verification, audit).
9. **LLM analysis layer** (structured reasoning + explanation, with post-validation and fallback).
10. **External enrichment:** CDSCO batch-match scenario first (strong demo moment), then Open-Meteo, WHO normalization, NPPA reference.
11. **Supplier intelligence** + procurement view (incl. UNKNOWN supplier).
12. **Polish:** failure banners, data freshness, docs, optional question mode, deployment.

If time runs short, cut from the bottom (question mode, NPPA, extra triggers) — never cut verification.

---

## 25. Known Conflicts and Open Decisions

Flagged rather than silently resolved. Resolve explicitly and update this section.

| # | Item | Resolution used for now |
|---|---|---|
| 1 | Original submission lists "PostgreSQL / DuckDB" as the data store; current direction specifies PostgreSQL | **PostgreSQL** is the system of record. DuckDB is not used unless explicitly decided later (e.g., for benchmark analytics). |
| 2 | Original flow is `QUESTION → …`; current direction is autonomous detection | Autonomous detection is primary. Question mode is optional and feeds the same pipeline. |
| 3 | Redis/queue infrastructure is excluded for MVP, though the owner's general stack interests include it | Not used in this project's MVP. In-process scheduler or manual trigger is enough. |
| 4 | WHO ICD is not a prevalence source | Disease concentration signals come from the client's (synthetic) `disease_data`; WHO is for normalization only. |
| 5 | CDSCO/NPPA retrieval method (structured download vs. scraping) is undecided | Pick the most reliable option; cache raw snapshots; never fabricate on failure. |
| 6 | Which LLM (OpenAI vs Gemini) handles which task | Config-driven behind `LLMClient`; decide empirically. |
| 7 | Stockout probability method (normal approximation vs Monte Carlo) | Start with documented normal approximation; Monte Carlo optional with fixed seed. |
| 8 | Weather–disease relevance mapping and the form of `weather_adj`/`disease_adj` | Configurable, bounded, explicitly labelled as assumptions. Do not present as empirically validated. |

---

## 26. Do-Not-Build List

Do **not** spend MVP time on:

- Signup, login, JWT, RBAC, password reset, SSO
- Microservices, Kafka, Redis, Kubernetes, distributed infrastructure
- Complex agent frameworks / multi-agent orchestration
- Elaborate permission systems
- Unnecessary dashboards, CRUD admin screens, or settings pages
- Dozens of external APIs beyond WHO, Open-Meteo, CDSCO, NPPA
- Real-time collaboration
- Mobile application
- Autonomous execution of purchases/transfers
- LLM-computed numbers or an LLM-based verifier
- Fabricated benchmarks, fabricated supplier scores, fabricated alerts

---

## 27. Demo Scenario

One coherent story:

1. DecisionOS starts with (synthetic) client operational data and fresh external pulls (with visible freshness).
2. The scan discovers: **Medicine X in Hyderabad** has rising demand, relevant disease concentration, seasonal uplift, a weather signal, significant stock, approaching expiry, and a supplier lead-time constraint → a `decision_candidate` is created automatically.
3. **ANALYZE:** drivers identified with evidence references.
4. **SIMULATE:** (1) Do nothing, (2) Prioritize expiring inventory, (3) Redistribute, (4) Reorder, (5) Change supplier if procurement is needed.
5. **DECIDE:** action selected from quantified trade-offs under constraints.
6. **VERIFY:** the verifier independently recomputes the critical claims → `✓ Independently Verified`.
7. **OUTPUT:** recommendation, expected impact, evidence, verification, audit trail → human approves.
8. **Failure demo (important):** deliberately inject an incorrect AI-side number → verifier mismatch → decision shows **WITHHELD** with AI vs verifier values side by side.
9. **CDSCO demo:** a CDSCO NSQ record for Product X / Batch ABC123 matches a client batch exactly → `CRITICAL` quality candidate; show that a *different* batch of the same product is **not** flagged.
10. **Supplier demo:** procurement view with three suppliers, one of which has UNKNOWN history displayed as such.

---

## 28. Agent Rules

Every coding agent working in this repository MUST:

1. Read `project_details.md` first.
2. Treat it as the product source of truth.
3. Preserve the ANALYZE → SIMULATE → DECIDE → VERIFY architecture.
4. Never move critical calculations into an LLM.
5. Never remove independent verification to simplify implementation.
6. Never fabricate external data.
7. Never fabricate supplier quality/reliability.
8. Never treat missing data as zero.
9. Never expose secrets.
10. Never add large infrastructure without necessity.
11. Prefer deterministic code for critical business logic.
12. Write tests for important calculations.
13. Preserve evidence/auditability.
14. Clearly mark synthetic demo data.
15. Keep external integrations modular so failures do not destroy the whole system.
16. Make the smallest implementation that satisfies the requirement.
17. Do not refactor unrelated code while implementing a feature.
18. Do not introduce dependencies without justification.
19. Do not create unnecessary UI.
20. If a requirement conflicts with this document, flag the conflict rather than silently choosing one interpretation.

Additional constraints implied by this spec:
- The verification module must not import simulation or decision code.
- A `WITHHELD` decision must never be shown as a released recommendation or be approvable.
- Do not state benchmark numbers that have not been measured.

---

## 29. First Task for the Coding Agent

**Do NOT implement the whole application first.** Inspect the existing repository and report:

- Current frontend (framework, version, structure)
- Current backend (framework, structure)
- Existing files and directories
- Existing dependencies (and anything conflicting with the stack here)
- Existing database configuration
- Existing `.env` structure and whether `.env` is git-ignored
- Existing components/pages
- What can be reused
- What should be removed or refactored (and why)

Then produce a **concise implementation plan** mapped to the build order in Section 24, listing files to create/modify. Do not rewrite the repository blindly. Wait for confirmation if the plan involves deleting existing work.

---

## 30. Glossary

| Term | Meaning |
|---|---|
| FEFO | First-Expiry-First-Out: consume earliest-expiring batches first |
| NSQ | Not of Standard Quality (CDSCO designation) |
| CDSCO | Central Drugs Standard Control Organization (India) |
| NPPA | National Pharmaceutical Pricing Authority (India) |
| WHO ICD | World Health Organization International Classification of Diseases (API) |
| Decision candidate | A detected situation that may require a decision |
| Decision package | Recommendation + impact + evidence + verification + audit trail |
| WITHHELD | Recommendation not released because verification failed |
| UNKNOWN | Explicit state for missing supplier reliability/quality history; never defaulted |
| Inputs snapshot | Immutable copy (and hash) of the data used for a simulation |
| Synthetic client data | Generated demo data standing in for a real client's database |