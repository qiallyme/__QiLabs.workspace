# strict-compliance

# QIOS_GLOBAL_ENFORCEMENT_MODE

You are operating inside the QiOS architecture.

This is not a normal codebase.
This is a governed system with constitutional doctrine, canonical placement rules, schema authority, tenant isolation, and spine-first ingestion.

Your job is not to be clever.
Your job is to preserve coherence.

Before ANY planning, implementation, schema design, refactor, architectural suggestion, data model change, worker design, API contract, or feature expansion, you MUST perform a doctrine alignment step.

Read-only repo discovery is allowed before doctrine review ONLY when needed to locate files, inspect current state, or generate an audit. Discovery must not modify files.

---

# 0. SAFE DISCOVERY EXCEPTION

You MAY perform read-only inspection before full doctrine review when the task is:

- locating blueprint files
- auditing current repo state
- listing files/directories
- identifying generated output
- finding duplicates
- finding hardcoded paths
- determining what files are relevant
- producing an inventory report

During Safe Discovery:

- DO NOT modify files
- DO NOT generate implementation code
- DO NOT refactor
- DO NOT rename/move/delete
- DO NOT infer new architecture
- DO NOT treat implementation as authority over doctrine

Safe Discovery output mode must be:

## MODE 4 — Audit / Review

After discovery, doctrine review is required before recommendations become implementation plans.

---

# 1. MANDATORY DOCTRINE REVIEW

Before taking action beyond Safe Discovery, you MUST review the applicable blueprint files.

## Core Governance

Required for every planning, design, implementation, refactor, schema, architecture, or feature task:

- `./__QiOS_Master_Blueprint_v0.4/docs/01_governance/policies.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/01_governance/standards.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/03_structure/placement_rules.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/04_data/schema.md`

If these files are missing, renamed, relocated, or unavailable:

STOP.

Return an Out-of-Bounds Alert stating that doctrine authority cannot be loaded.

---

# 2. CONTEXTUAL DOCTRINE LOADING

Load additional doctrine based on task type.

## Structure / Objects

If the task involves structure, folders, object ownership, canonical placement, object lifecycle, registries, or cross-domain placement, review:

- `./__QiOS_Master_Blueprint_v0.4/docs/03_structure/object_model.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/04_data/objects.md`

## Data / Storage

If the task involves databases, storage, tables, files, blobs, records, metadata, archive state, or persistence, review:

- `./__QiOS_Master_Blueprint_v0.4/docs/04_data/storage.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/04_data/metadata.md`

## Pipelines / Ingestion / Automation

If the task involves import, ingestion, OCR, AI enrichment, workers, queues, automations, sync, external APIs, file processing, or derived outputs, review:

- `./__QiOS_Master_Blueprint_v0.4/docs/05_compute/pipelines.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/05_compute/integrations.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/05_compute/workers.md`

## System Design / Cross-Domain Architecture

If the task affects system boundaries, app architecture, service boundaries, platform design, runtime zones, deployment, or cross-domain contracts, review:

- `./__QiOS_Master_Blueprint_v0.4/docs/02_architecture/`
- `./__QiOS_Master_Blueprint_v0.4/docs/01_governance/decisions.md`

## History / Rules / Doctrine Changes

If the task affects doctrine, history, standards, policies, ADRs, changelogs, naming rules, placement rules, schema rules, or constitutional behavior, review:

- `./__QiOS_Master_Blueprint_v0.4/docs/appendices/changelog.md`
- `./__QiOS_Master_Blueprint_v0.4/docs/adr/`

Any doctrine change requires ADR consideration.

---

# 3. NON-NEGOTIABLE QIOS LAWS

You MUST enforce these at all times.

## 1. Three-Band Model

Only these bands exist:

1. Core
2. Platform
3. Domain

Rules:

- Core may define system doctrine and foundational rules.
- Platform may provide shared services and reusable capabilities.
- Domain may implement domain-specific behavior.
- No reverse dependency.
- No band leakage.
- Domain logic must not live in Core.
- Core doctrine must not be redefined downstream.

## 2. Single Domain Rule

Every object has ONE canonical home.

Rules:

- No duplicate canonical objects.
- No second “temporary truth” table.
- No shadow object lifecycle.
- No parallel placement because it feels convenient.
- If ownership is unclear, STOP and escalate.

## 3. No Domain Logic in `public` Schema

The `public` schema is auth-adjacent/global only.

Rules:

- NEVER place domain tables in `public`.
- NEVER place domain workflows in `public`.
- NEVER place business objects in `public`.
- Domain data belongs in its owning domain schema.

## 4. Tenant Isolation Is Mandatory

Every domain table MUST include:

- `tenant_id`

Rules:

- RLS is required.
- RLS is not optional.
- Tenant isolation cannot be deferred.
- “We’ll add RLS later” is forbidden.
- Any exception requires explicit ADR approval.

## 5. Spine-First Ingestion

Nothing becomes canonical without QiArchive registration.

Rules:

- No direct writes from UI to final canonical domain tables unless doctrine explicitly allows it.
- No direct writes from integrations to final canonical domain tables.
- Ingestion must flow through the archive/spine layer.
- Canonicalization happens after registration, classification, validation, and promotion.

## 6. Derived Is Not Truth

These are downstream only:

- AI outputs
- summaries
- embeddings
- vector stores
- graph projections
- search indexes
- exports
- reports
- dashboards
- generated docs
- static site output

Rules:

- Derived artifacts NEVER define canonical state.
- Derived artifacts may be regenerated.
- Derived artifacts must point back to canonical source where possible.

## 7. No Parallel Systems

Do not create:

- duplicate schemas
- duplicate pipelines
- duplicate registries
- duplicate vault roots
- shadow APIs
- second source of truth
- alternate object lifecycle

If the requested solution creates a parallel system, STOP.

## 8. Schema Authority

Supabase migrations are canonical for database truth.

Rules:

- Docs describe.
- Migrations define.
- Generated types follow migrations.
- Implementation must not contradict migrations.
- If docs and migrations disagree, flag drift.

## 9. Generated Output Is Not Source

Generated output must not be treated as canonical source.

Examples:

- `dist/`
- `build/`
- `.vitepress-dist/`
- static HTML exports
- generated JS chunks
- search indexes
- generated docs
- `.lean.js` output
- compiled assets

Rules:

- Do not edit generated output as source.
- Find and modify original source files.
- If source is missing, flag as drift/missing source.
- Generated output should usually live under `_dist/` or be gitignored.

## 10. Local Access Must Be Permissioned

Any local file access must be constrained.

Rules:

- No arbitrary filesystem browsing by default.
- No unrestricted local file manager behavior.
- No path traversal.
- No access outside approved roots.
- All local roots must be configured, not scattered.
- Notes/vault access must be limited to approved vault paths.

---

# 4. PRE-ACTION VALIDATION

Before proposing any solution, internally answer:

1. What band does this belong to?
2. What schema owns this object’s lifecycle?
3. Does this require `archive_id`?
4. Does this require `tenant_id`?
5. Is this canonical or derived?
6. Does this violate Spine flow?
7. Is this source or generated output?
8. Does it introduce a parallel system?
9. Does it create a second source of truth?
10. Does it require an ADR?

If any answer is unclear:

STOP.

Return an Out-of-Bounds Alert or an Audit/Review finding.

---

# 5. REPO-AWARE VALIDATION

Before writing anything, inspect relevant repo areas.

Expected areas may include:

- `/packages/database/src/migrations/`
- `/packages/database/src/schemas/`
- `/python_local/`
- `/workers/`
- `/apps/`
- `/packages/`
- `/src/`
- `/public/`
- `/docs/`
- `/scripts/`
- `/config/`

Use repo state for alignment, but:

- NEVER let implementation override doctrine.
- Blueprint doctrine is the authority for architecture.
- Supabase migrations are the authority for database truth.
- Generated output is not source.

If expected directories are missing, report that clearly.

Do not invent missing structure without approval.

---

# 6. OUT-OF-BOUNDS PROTOCOL

If a requested solution violates any QiOS law:

DO NOT CONTINUE.

Return exactly this structure:

## 🚨 Out-of-Bounds Alert

### 1. Deviation

State the exact rule being broken.

### 2. Ripple-Check

Impact on:

- RLS
- Spine
- Band model
- Schema ownership
- Workers / pipelines
- Source of truth
- Generated/derived layers

### 3. Pros & Cons

Give a brutally honest tradeoff analysis.

### 4. Approval Request

Ask the user to confirm whether to proceed by creating or updating an ADR.

Use:

`/update-adr`

NO CODE.  
NO PARTIAL IMPLEMENTATION.  
NO “quick workaround.”

---

# 7. ALLOWED OUTPUT MODES

Respond in exactly ONE mode per task.

---

## MODE 1 — Doctrine Patch

Use for blueprint updates, rule edits, standards, ADR preparation, governance changes.

Required sections:

- Compliance Review
- Patch Plan
- Exact Markdown Changes
- Consistency Check
- Rejected Alternatives

---

## MODE 2 — Implementation Plan

Use for feature planning or architecture after doctrine validation.

Required sections:

- Domain Placement
- Band Placement
- Data Model
- Schema Alignment
- Pipeline Flow
- Spine Compliance
- API / Worker Contracts
- Risks
- Do-Not-Cross Lines

---

## MODE 3 — Code Generation

Use only after validation.

Required rules:

- Reference schema and band.
- Respect ingestion flow.
- Do not invent structure.
- Do not write to generated output.
- Do not create domain tables in `public`.
- Include migration impact if applicable.
- Include rollback notes if modifying behavior.

---

## MODE 4 — Audit / Review

Use for inspection, drift detection, file analysis, repo reports, cleanup reviews, and compliance checks.

Required sections:

- Scope
- Evidence
- Violations Found
- Drift Detected
- Fluff / Generated Output
- Duplicate Candidates
- Missing Sources
- Risk Level
- Fix Recommendations
- Do-Not-Touch List

MODE 4 may be performed under Safe Discovery.

---

# 8. NOTES / VAULT / LOCAL FILE ACCESS RULES

QiAccess may act as a permissioned control surface.

It must not become an uncontrolled file browser.

## Notes Gateway Doctrine

If implementing notes, vault, Markdown, capture, or local file access:

- Use one configured vault root.
- Do not hardcode scattered paths.
- Do not allow arbitrary filesystem browsing.
- Do not write outside approved vault paths.
- Do not treat generated docs as source notes.
- Do not create a second canonical vault.
- Server/local tools may read broadly only inside approved roots.
- Server/local tools may write only to approved controlled folders unless explicitly authorized.

Preferred controlled note paths:

- `00_inbox/`
- `20_timeline/daily/`
- `10_workbench/`
- `_system/generated/`

Preferred routes:

- `/notes/capture`
- `/notes/daily`
- `/notes/workbench`
- `/notes/search`

If notes functionality is unclear, classify it first as one of:

- controlled gateway
- file browser
- Markdown editor
- static docs viewer
- placeholder
- unclear

Do not expand it until classified.

---

# 9. CLEANUP / ARCHIVE RULES

Before deleting or moving files:

1. Audit first.
2. Classify files.
3. Identify source vs generated output.
4. Identify dependencies.
5. Create rollback path.
6. Prefer archive over delete.
7. Confirm app still builds/runs.
8. Confirm docs still build/render.
9. Confirm links still resolve.

Generated output may be archived or regenerated, but only after source files are confirmed.

Do not delete:

- source code
- migrations
- schema files
- canonical Markdown doctrine
- `.env.example`
- app config
- worker config
- unresolved audit files
- unknown files with possible source authority

---

# 10. SUCCESS CRITERIA

A valid response must:

- Preserve single source of truth.
- Maintain strict domain ownership.
- Respect tenant isolation.
- Follow Spine ingestion rules.
- Keep derived layers downstream.
- Avoid schema drift.
- Avoid generated-output edits.
- Avoid uncontrolled local file access.
- Remain composable across the system.
- Prefer coherence over convenience.
- Prefer boring structure over clever shortcuts.

If it feels clever but breaks structure, it is wrong.

---

# 11. DEFAULT BEHAVIOR

When in doubt:

1. Audit.
2. Load doctrine.
3. Classify band/domain/source-of-truth.
4. Identify risks.
5. Ask for ADR if rules would change.
6. Implement only after alignment.

Do not improvise architecture.
Do not create parallel truth.
Do not normalize chaos.
