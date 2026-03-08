# R&D PIPELINE BRIEFING — Agent Operating Manual

**Prepared by:** Project/Concept Owner
**Date:** 2026-03-08
**Classification:** Internal — All 5 Agents
**Source Files Reviewed:** rnd.py, rnd_doctrine.py, doctrine.py, strategy.py, council.py, seed_charlotte.py, GOVERNANCE.md, all agents/, all warehouse/

---

## BUSINESS CONTEXT (Read This First)

Corporate is a solo-operated barbershop business in Charlotte, NC. The owner operates from a solo suite in South Park (zip 28210), generating ~$42,000/year ($3,500/month). The strategic goal is to **transition from a solo suite to a full shop** with chair rentals, retail product sales, and a premium service tier.

The business has five compounding assets:

| # | Asset | What It Is |
|---|-------|-----------|
| 1 | THE CRAFT | 10 years of barbering expertise — fades, skin fades, beards, kids |
| 2 | THE DEGREE | Formal business degree — strategy, finance, market analysis |
| 3 | THE AI | Claude as research partner, analyst, and builder |
| 4 | THE OS | Proprietary booking system backed by a data warehouse (migrating from Booksy) |
| 5 | THE WAREHOUSE | Major product distributor membership — wholesale access, 50-70% retail margins |

The core mission from `doctrine.py`: **Survival through strategic adaptation — win today while preparing for tomorrow.**

The R&D mission from `rnd_doctrine.py` Section 1: **Convert uncertainty into validated advantage.**

---

## SECTION 1: VISION ALIGNMENT CHECK

### The Core Vision

Transition from solo suite operator ($42K/year) to shop owner with multiple revenue streams ($75K-$120K+/year), using five compounding assets as the foundation. Every R&D project must serve this exit ramp.

### Project-to-Vision Mapping (All 20 Projects)

#### SERVICE LAB (3 projects) — "What else can your hands create?"

| # | Project | Status | Priority | Vision Alignment | Verdict |
|---|---------|--------|----------|-----------------|---------|
| 1 | Royal Treatment Premium Tier ($75+) | Research | HIGH | DIRECT — adds $7,800-$11,700/yr, proves premium positioning to landlords | ALIGNED |
| 2 | Membership / Subscription Model | Research | MEDIUM | DIRECT — converts irregular clients to predictable monthly revenue, critical for lease applications | ALIGNED |
| 3 | Group / Event Booking Package | Idea | LOW | INDIRECT — fills dead slots, but requires shop space (events don't work in a suite) | ALIGNED but premature — needs shop first |

#### OS LAB (5 projects) — "What should the OS do next?"

| # | Project | Status | Priority | Vision Alignment | Verdict |
|---|---------|--------|----------|-----------------|---------|
| 4 | Booksy Migration Completion | In Progress | CRITICAL | FOUNDATIONAL — the OS is asset #4, cannot run a shop on someone else's platform | ALIGNED — #1 priority |
| 5 | Client Analytics Dashboard | Research | HIGH | DIRECT — data-driven decisions, proves business intelligence to landlords/lenders | ALIGNED |
| 6 | Chair Rental Management Module | Idea | MEDIUM | DIRECT — manages $12K-$36K/yr in chair rental revenue, core to shop model | ALIGNED — needs activation when shop secured |
| 7 | Dynamic Pricing Engine | Idea | LOW | INDIRECT — optimization play, not needed until shop is operational | ALIGNED but distant |
| 8 | OS Licensing Research | Idea | LOW | TANGENTIAL — potential SaaS revenue ($24K-$60K/yr) but a completely different business | CAUTION — resource distraction risk |

#### MARKET LAB (3 projects) — "Where is the opportunity?"

| # | Project | Status | Priority | Vision Alignment | Verdict |
|---|---------|--------|----------|-----------------|---------|
| 9 | Client Geography Analysis | Research | HIGH | CRITICAL — prevents a $50K+ location mistake, directly feeds shop site selection | ALIGNED |
| 10 | Grooming Product Market Research | Research | MEDIUM | DIRECT — informs product lab, maximizes retail margin per square foot | ALIGNED |
| 11 | Charlotte Barber Market Sizing | Idea | MEDIUM | SUPPORTING — quantifies TAM, informs all expansion decisions | ALIGNED |

#### BUSINESS LAB (4 projects) — "How do you fund and structure the next move?"

| # | Project | Status | Priority | Vision Alignment | Verdict |
|---|---------|--------|----------|-----------------|---------|
| 12 | Lease Negotiation Playbook | Research | HIGH | CRITICAL — saves $5K-$15K over lease term, directly enables the exit | ALIGNED |
| 13 | Shop P&L Financial Model | Research | HIGH | CRITICAL — the decision tool for the entire exit, landlord/lender-ready | ALIGNED |
| 14 | Barber Consulting Service | Idea | LOW | TANGENTIAL — a different business line, only viable after own shop is proven | CAUTION — premature |
| 15 | Small Business Grant / Funding Research | Idea | MEDIUM | DIRECT — $5K-$50K in non-dilutive capital for shop build-out | ALIGNED |

#### PRODUCT LAB (5 projects) — "How do you turn wholesale access into a revenue engine?"

| # | Project | Status | Priority | Vision Alignment | Verdict |
|---|---------|--------|----------|-----------------|---------|
| 16 | Retail Product Selection Strategy | Research | HIGH | DIRECT — $3,600-$7,200/yr retail margin, builds brand environment in shop | ALIGNED |
| 17 | Product-Service Bundles | Research | HIGH | DIRECT — $4,000-$8,000/yr incremental, raises average ticket 30-50% | ALIGNED |
| 18 | Grooming Subscription Box | Idea | MEDIUM | INDIRECT — recurring revenue without chair time, but operationally complex for a solo operator | ALIGNED but premature |
| 19 | Chair Renter Supply Program | Idea | MEDIUM | DIRECT — makes your chairs stickier, $2,400-$7,200/yr margin, differentiated value prop | ALIGNED |
| 20 | Private Label Feasibility Study | Idea | LOW | ASPIRATIONAL — $10K-$30K/yr potential but high MOQ risk, requires established retail presence | CAUTION — long-horizon |

### Vision Alignment Summary

- **18 of 20 projects** align with the core vision (suite-to-shop transition)
- **2 projects** carry tangential risk: OS Licensing (#8) and Barber Consulting (#14) — both are "different business" plays that could distract from the exit ramp
- **1 project is the #1 priority across all labs:** Booksy Migration (#4) — the entire system depends on it

---

## SECTION 2: TARGET & METRIC INVENTORY

### Projects WITH Clear Quantitative Targets

| # | Project | Success Metric | Revenue Target | Measurability |
|---|---------|---------------|----------------|---------------|
| 1 | Royal Treatment | 2-3 bookings/week within 60 days | $7,800-$11,700/yr | STRONG — bookings counted via OS |
| 2 | Membership Model | 10 members in 90 days, churn <15%/mo | $6,000-$12,000/yr | STRONG — member count, churn rate |
| 3 | Group Booking | 1 group/month at $200+ avg ticket | $2,400-$4,800/yr | MODERATE — low frequency makes signal noisy |
| 4 | Booksy Migration | Zero Booksy bookings, all on OS, no data loss | Saves $360/yr + protects relationships | BINARY — clear pass/fail |
| 5 | Analytics Dashboard | 6 KPIs operational, auto-updated | Indirect | MODERATE — KPIs defined but "operational" is subjective |
| 6 | Chair Rental Module | Track 1-3 renters, automated billing/utilization | Manages $12K-$36K/yr | STRONG — billing is measurable |
| 7 | Dynamic Pricing | 10% increase in off-peak utilization in 90 days | $2,000-$5,000/yr | STRONG — utilization tracked by OS |
| 8 | OS Licensing | Market sizing done, 5 pilots identified, pricing drafted | $24K-$60K/yr (at scale) | WEAK — outputs are documents, not results |
| 9 | Client Geography | Heat map + top 3 zips + cross-ref with competitor density | Prevents $50K+ mistake | MODERATE — deliverable-based, not outcome-based |
| 10 | Product Market Research | Top 5 lines with margin analysis | $3,600-$7,200/yr | MODERATE — research output, not revenue validation |
| 11 | Market Sizing | Market size estimate, growth rate, segments | Indirect | WEAK — research deliverable only |
| 12 | Lease Playbook | 10+ tactics, term sheet template, red flag checklist | Saves $5K-$15K | MODERATE — deliverable count, savings estimated |
| 13 | Shop P&L Model | 3 scenarios, break-even, sensitivity analysis | Indirect (decision tool) | STRONG — model structure well defined |
| 14 | Consulting Service | 3 conversations, pricing model drafted | $5K-$20K/yr | WEAK — "conversations" is thin |
| 15 | Grant Research | 5+ programs identified, 2 applications drafted | $5K-$50K | MODERATE — identifiable programs, but award is external |
| 16 | Product Selection | Top 10 SKUs, margin analysis, reorder points, 90-day projection | $3,600-$7,200/yr | STRONG — SKU-level tracking |
| 17 | Product-Service Bundles | 3 bundles designed, +$15/bundled visit tracked via OS | $4,000-$8,000/yr | STRONG — OS tracks ticket size |
| 18 | Subscription Box | 15 subscribers in 90 days, churn <20%/mo, $10+ margin/box | $4,500-$14,400/yr | STRONG — subscriber count, margin per box |
| 19 | Chair Renter Supply | 2+ renters buying through you, $100+/mo margin each | $2,400-$7,200/yr | STRONG — sales tracked per renter |
| 20 | Private Label | MOQ/cost research, 2-3 categories, break-even | $10,000-$30,000/yr | WEAK — research phase only, no validation gate |

### Projects Lacking Clear Targets (Agent 2 Action Items)

1. **OS Licensing (#8)** — Has deliverable targets but no validation criteria. When does "feasibility" become a go/no-go?
2. **Charlotte Market Sizing (#11)** — Pure research output with no decision trigger. What number changes the strategy?
3. **Barber Consulting (#14)** — "3 conversations" is not a metric. Needs: willingness-to-pay signal, pipeline value.
4. **Private Label (#20)** — Break-even is calculated but there is no stated go/no-go threshold.

### Aggregate Revenue Potential

| Category | Conservative | Optimistic |
|----------|-------------|------------|
| Direct revenue projects | $48,300/yr | $118,500/yr |
| Cost savings | $5,360/yr | $15,360/yr |
| Indirect/decision value | Prevents $50K+ mistakes | Enables $75K-$120K+ run rate |

---

## SECTION 3: TRADE-OFF MATRIX

### Resource Conflicts

The business has ONE operator. Every project competes for the same person's time, attention, and energy. This is the fundamental constraint.

#### Conflict 1: BUILDING vs. CUTTING
- R&D work (building the OS, doing market research, writing playbooks) takes time away from the chair
- Chair time = $42K/yr in revenue
- **Hard choice:** Every hour on R&D is $35-65 in lost haircut revenue
- **Resolution:** R&D work happens outside chair hours. The AI (Claude) is the force multiplier that makes this possible.

#### Conflict 2: BOOKSY MIGRATION vs. EVERYTHING ELSE IN OS LAB
- Project #4 (Booksy Migration) is marked CRITICAL and IN PROGRESS
- Projects #5-8 all depend on the OS being the single source of truth
- **Hard choice:** No other OS project should advance until migration is complete
- **Resolution:** Sequential gating. Migration first. Everything else queues.

#### Conflict 3: PRODUCT LAB vs. SERVICE LAB for Average Ticket Growth
- Royal Treatment (#1) raises ticket via premium service ($75+)
- Product-Service Bundles (#17) raises ticket via product add-on (+$15)
- Both target the same goal (higher average ticket) but through different mechanisms
- **Hard choice:** Which do you launch first? Both need client willingness research.
- **Resolution:** These are complementary, not competitive. Bundle is lower risk (product cost is sunk via wholesale). Launch bundles first to test willingness, then layer premium service.

#### Conflict 4: SUITE OPTIMIZATION vs. SHOP PREPARATION
- Projects #1, #2, #17 optimize the suite (make more money now)
- Projects #9, #12, #13, #15 prepare for the shop (invest for later)
- **Hard choice:** The doctrine says "win today while preparing for tomorrow" — but how much time on each?
- **Resolution:** Phase 1 of the council's ramp: stack revenue in the suite while building the financial case. These are parallel tracks, not trade-offs — but they must be time-boxed.

#### Conflict 5: SUBSCRIPTION BOX (#18) vs. CHAIR RENTER SUPPLY (#19) for WAREHOUSE asset utilization
- Both use wholesale access
- Subscription box targets end consumers (B2C, operationally complex: shipping, packaging, curation)
- Chair renter supply targets barbers (B2B, operationally simple: they pick up at the shop)
- **Hard choice:** Which captures more value from the wholesale membership?
- **Resolution:** Chair renter supply is the clear first move — it only works once you have a shop and renters, but it is zero-logistics margin. Subscription box is Phase 2.

#### Conflict 6: OS LICENSING (#8) vs. CORE BUSINESS FOCUS
- OS licensing is a SaaS play ($24K-$60K/yr at scale)
- It requires: productization, support, documentation, sales — a completely different business
- **Hard choice:** The OS is currently a competitive weapon. Licensing it means sharing the advantage.
- **Resolution:** Park this firmly in the "idea" stage. Do not advance until the shop is operational and profitable for 12+ months. The doctrine says: "value before novelty."

### Attention Competition Matrix

| Resource | Projects Competing | Winner |
|----------|--------------------|--------|
| Owner's chair hours | All service/product projects vs. all research projects | Chair hours are sacred — R&D is off-hours |
| OS development time | Migration (#4) vs. Dashboard (#5) vs. Chair Module (#6) vs. Dynamic Pricing (#7) | Migration first, then Dashboard |
| Wholesale buying power | Product Selection (#16) vs. Bundles (#17) vs. Subscription (#18) vs. Chair Supply (#19) vs. Private Label (#20) | Selection (#16) first — you need to know WHAT to buy before anything else |
| Financial modeling energy | Shop P&L (#13) vs. Lease Playbook (#12) vs. Grant Research (#15) | P&L model (#13) first — it feeds the lease negotiation and grant applications |
| Client relationship capital | Membership (#2) vs. Premium Tier (#1) vs. Bundles (#17) | Don't overwhelm clients with 3 new things — stagger launches 30 days apart |

---

## SECTION 4: CONCEPT PAPER STATUS

### What the Doctrine Requires (rnd_doctrine.py, Section 5A)

Every R&D initiative must begin with a **Concept Paper** that defines:
- Target customer
- Problem worth solving
- Product or capability vision
- Key requirements
- Non-negotiable constraints
- Cost, timing, and performance targets
- Major risks
- Ownership and team roles

### Current Status: ZERO Formal Concept Papers Exist

None of the 20 projects have formal concept papers. They have:
- Descriptions (all 20)
- Hypotheses (all 20)
- Success metrics (all 20)
- Revenue potential estimates (all 20)
- Assets used (all 20)

This is a strong seed — better than most R&D pipelines at this stage — but it falls short of the doctrine's Concept Paper standard. The current project records are stored as database rows in `rnd_projects` with text fields. They are not structured documents.

### Concept Paper Priority (which projects need them first)

**TIER 1 — Need Concept Papers NOW** (active/critical projects):
1. Booksy Migration (#4) — IN PROGRESS, CRITICAL, no concept paper
2. Royal Treatment Premium Tier (#1) — RESEARCH, HIGH
3. Shop P&L Financial Model (#13) — RESEARCH, HIGH
4. Lease Negotiation Playbook (#12) — RESEARCH, HIGH
5. Client Geography Analysis (#9) — RESEARCH, HIGH

**TIER 2 — Need Concept Papers SOON** (high-priority research):
6. Client Analytics Dashboard (#5) — RESEARCH, HIGH
7. Retail Product Selection (#16) — RESEARCH, HIGH
8. Product-Service Bundles (#17) — RESEARCH, HIGH
9. Membership Model (#2) — RESEARCH, MEDIUM

**TIER 3 — Can Wait** (idea-stage projects):
10-20. All remaining projects in "idea" status. Concept papers should be drafted when a project moves from "idea" to "research."

### Gap Between Current State and Doctrine Compliance

The `rnd_doctrine.py` audit function checks 7 decision rules per project:
1. Problem is real (has description >20 chars) -- ALL PASS
2. Customer value identifiable (has revenue potential) -- ALL PASS
3. Strategy aligned (uses at least 1 asset) -- ALL PASS
4. Technical path plausible (status beyond idea) -- ACTIVE PROJECTS PASS
5. Learning plan defined (has hypothesis) -- ALL PASS
6. Risks visible (has hypothesis) -- ALL PASS (but this is a proxy, not a real risk register)
7. Success measurable (has success metric) -- ALL PASS

**Assessment:** The automated audit will show 100% compliance for active projects, but this is a **false positive**. Having a hypothesis field is not the same as having a structured Concept Paper with constraints, risks, and team roles. The audit needs hardening.

---

## SECTION 5: AGENT ASSIGNMENTS

### Agent 1: Vision Coherence Auditor

**Mission:** Ensure every R&D project ladders up to the core vision (suite-to-shop transition with compounding assets).

**Responsibilities:**
- Maintain the project-to-vision map in Section 1 above
- Flag any new project that does not connect to the exit ramp within 2 degrees
- Quarterly review: are the 2 tangential projects (#8 OS Licensing, #14 Consulting) still parked? If anyone is working on them, pull the brake
- Validate that every project names which of the 5 assets it leverages (rnd_doctrine.py operating rule)
- Cross-check against `doctrine.py` strategic leadership principles: Environmental Awareness, Organizational Alignment, Intelligence Development, Strategic Adaptability, Opportunity Creation

**Key Files:**
- `/home/user/Corporate-/rnd.py` — project definitions, asset mappings (lines 277-523)
- `/home/user/Corporate-/doctrine.py` — strategic doctrine, especially `strategic_leadership` section
- `/home/user/Corporate-/strategy.py` — YOUR_SHOP config (lines 27-69), the baseline reality

**Current Red Flags:**
1. OS Licensing (#8) could absorb unlimited time if not contained
2. Barber Consulting (#14) is a ego project masquerading as R&D until proven otherwise
3. Group Booking (#3) requires a shop but is listed in service lab — mark as "blocked by shop transition"

**Decision Rule:** If a project cannot answer "How does this get us from suite to shop, or make the shop more successful?" in one sentence, it does not belong in active R&D.

---

### Agent 2: Metric & Target Tracker

**Mission:** Own the numbers. Every project has a metric. Every metric has a tracking method. No vanity metrics.

**Responsibilities:**
- Maintain the metric inventory in Section 2 above
- For each project, define: (a) the metric, (b) the data source, (c) the tracking cadence, (d) the go/no-go threshold
- Flag projects with weak metrics (see Section 2 action items: #8, #11, #14, #20)
- Track aggregate revenue potential across the pipeline — current estimate: $48K-$118K/yr direct, $5K-$15K/yr in savings
- Build a dashboard view that shows: projects by status, revenue potential by lab, metric completion rate

**Key Files:**
- `/home/user/Corporate-/rnd.py` — `success_metric` and `revenue_potential` fields in project seeds (lines 277-523)
- `/home/user/Corporate-/rnd_doctrine.py` — Section 10: "Metrics That Matter" (lines 289-309)
- `/home/user/Corporate-/strategy.py` — YOUR_SHOP financial baseline (annual_gross: $42,000)

**Immediate Actions:**
1. Harden metrics for projects #8, #11, #14, #20 — add explicit go/no-go thresholds
2. For projects #1 and #2 (Royal Treatment, Membership), define the "fail" signal — at what point do we kill or pivot?
3. Create a monthly revenue tracking template that maps actual vs. projected for launched projects
4. Validate that the OS can actually track the metrics claimed (e.g., "average ticket increase" requires transaction-level data flowing through the proprietary OS)

**Key Metric from the Doctrine (Section 10):** "% of projects producing reusable knowledge assets" and "portfolio kill-rate before expensive commitment." Currently: 0 projects killed. The doctrine says a department that never kills weak ideas is drunk.

---

### Agent 3: Trade-off Negotiator

**Mission:** Flag conflicts between projects. Negotiate resource allocation. Enforce sequencing discipline.

**Responsibilities:**
- Maintain the trade-off matrix in Section 3 above
- When a new project is proposed, run it through the conflict check: does it compete for the same resource, customer, or attention as an existing project?
- Enforce the sequential gates:
  - Gate 1: Booksy Migration must complete before any other OS Lab project advances
  - Gate 2: Product Selection (#16) must complete before Bundles (#17), Subscription (#18), or Private Label (#20)
  - Gate 3: Shop P&L (#13) must complete before Lease Playbook (#12) is finalized
  - Gate 4: Client Geography (#9) must complete before any lease is signed
- Protect chair hours — no R&D project may require the owner to cancel or reduce client appointments
- Manage the "client overwhelm" risk — no more than 1 new client-facing change per 30-day period

**Key Files:**
- `/home/user/Corporate-/council.py` — the 5 advisors each represent a different strategic lens; their vote logic (lines 616-691) encodes what "ready" looks like
- `/home/user/Corporate-/rnd.py` — project priorities and statuses
- `/home/user/Corporate-/strategy.py` — YOUR_SHOP config shows current constraints (solo operator, suite, $42K/yr)

**Current Critical Trade-off:**
The biggest unresolved tension is between "optimize the suite now" and "prepare for the shop." The council's ramp strategy says to do both in parallel, but with a single operator, parallel is an illusion. In practice, this means: mornings in the chair, evenings on R&D, weekends on research. Agent 3 must ensure this doesn't lead to burnout — the doctrine says "flow beats chaos."

---

### Agent 4: Concept Paper Manager

**Mission:** Track paper completeness for all 20 projects. Drive concept papers for active projects. Enforce doctrine Section 5A.

**Responsibilities:**
- Maintain the concept paper status tracker in Section 4 above
- For each active project (status = research or in_progress), ensure a concept paper exists with ALL required fields:
  - Target customer
  - Problem worth solving
  - Product or capability vision
  - Key requirements
  - Non-negotiable constraints
  - Cost, timing, and performance targets
  - Major risks
  - Ownership and team roles
- When a project moves from "idea" to "research," trigger concept paper creation
- Audit the existing `rnd_doctrine.py` audit function — it currently gives false positives (see Section 4 analysis)

**Key Files:**
- `/home/user/Corporate-/rnd_doctrine.py` — Section 5: "Doctrine of Work" (lines 136-179), audit function (lines 453-581)
- `/home/user/Corporate-/rnd.py` — project schema (lines 50-65), seed data (lines 277-523)

**Immediate Actions:**
1. Create concept paper template based on rnd_doctrine.py Section 5A requirements
2. Write concept papers for the 5 TIER 1 projects (Booksy Migration, Royal Treatment, Shop P&L, Lease Playbook, Client Geography)
3. Propose a concept paper storage mechanism — either extend the `rnd_projects` table with additional fields, or create a `rnd_concept_papers` table
4. Harden the audit function in `rnd_doctrine.py` to check for actual concept paper existence, not just field presence

**Doctrine Quote (Section 5A):** "This is not bureaucracy cosplay. It is the mechanism for aligning people, process, and tools before work begins."

---

### Agent 5: Stakeholder Communication Lead

**Mission:** Translate R&D status into language the owner understands. No jargon. No fluff. Actionable summaries.

**Responsibilities:**
- Produce a weekly R&D brief (1 page max) covering:
  - What moved forward this week
  - What is blocked and why
  - What decision is needed from the owner
  - Revenue impact of current pipeline
- Translate between the council advisors (council.py) and the R&D pipeline (rnd.py) — the council focuses on exit readiness, R&D focuses on project development, but they feed the same decision
- Maintain the owner-facing dashboard: which projects are worth talking about, which are background noise
- When a project hits a go/no-go gate, prepare the decision brief

**Key Files:**
- `/home/user/Corporate-/council.py` — council brief function (lines 699-723) is the model for concise communication
- `/home/user/Corporate-/rnd.py` — `show_pipeline()` function (lines 751-803) for current pipeline view
- `/home/user/Corporate-/strategy.py` — the owner's baseline reality and strategic context

**Communication Templates:**

**Weekly Brief Format:**
```
THIS WEEK:
  [project name] — [what happened] — [what it means]

BLOCKED:
  [project name] — [what's in the way] — [who can unblock it]

DECISION NEEDED:
  [describe the choice] — [option A vs B] — [recommendation]

PIPELINE HEALTH:
  [X] projects active | [Y] projects blocked | $[Z] revenue potential in play
```

**Current State Summary (for first brief):**
- 20 projects across 5 labs
- 1 project in progress (Booksy Migration — critical)
- 8 projects in research phase
- 11 projects in idea stage
- 0 projects completed, 0 killed
- Total pipeline revenue potential: $48K-$118K/yr direct
- Biggest risk: no concept papers exist yet
- Biggest blocker: Booksy migration must complete before OS Lab can advance
- Council vote status: likely 2-3 of 5 advisors vote "ready" (shop name not set, Booksy migration incomplete)

---

## APPENDIX A: PROJECT SEQUENCING RECOMMENDATION

### Phase 1 — NOW (next 30 days)
1. **Complete Booksy Migration (#4)** — unblocks everything in OS Lab
2. **Start Client Geography Analysis (#9)** — informs location decision
3. **Start Shop P&L Financial Model (#13)** — the decision tool
4. **Start Product-Service Bundles (#17)** — low-risk revenue lift in the suite

### Phase 2 — NEXT (days 30-90)
5. **Launch Royal Treatment Premium Tier (#1)** — prove premium demand
6. **Complete Lease Negotiation Playbook (#12)** — feeds from P&L model
7. **Build Client Analytics Dashboard (#5)** — leverage the migrated OS data
8. **Complete Retail Product Selection (#16)** — inform product inventory

### Phase 3 — LATER (days 90-180)
9. **Launch Membership Model (#2)** — layer on predictable revenue
10. **Start Grant/Funding Research (#15)** — fund the build-out
11. **Charlotte Market Sizing (#11)** — broader context for expansion

### Phase 4 — AFTER SHOP OPENS
12. **Activate Chair Rental Module (#6)**
13. **Launch Chair Renter Supply Program (#19)**
14. **Launch Grooming Subscription Box (#18)**
15. **Research Dynamic Pricing (#7)**

### Phase 5 — DISTANT HORIZON (12+ months post-shop)
16. **Group/Event Booking (#3)**
17. **OS Licensing Research (#8)**
18. **Barber Consulting (#14)**
19. **Private Label Study (#20)**

---

## APPENDIX B: KEY FILE REFERENCE

| File | Purpose | Key Lines |
|------|---------|-----------|
| `/home/user/Corporate-/rnd.py` | R&D department — 20 projects, 5 labs, 5 assets | Lines 277-523 (project definitions) |
| `/home/user/Corporate-/rnd_doctrine.py` | R&D operating constitution — 14 sections | Lines 29-387 (doctrine), 453-581 (audit) |
| `/home/user/Corporate-/doctrine.py` | Strategic intelligence doctrine — 9 principles | Lines 29-228 (doctrine), 296-723 (audit) |
| `/home/user/Corporate-/strategy.py` | Strategic playbook + YOUR_SHOP baseline | Lines 27-69 (config), rest is 6 strategy sections |
| `/home/user/Corporate-/council.py` | 5-advisor exit planning board | Lines 127-609 (advisors), 616-691 (vote) |
| `/home/user/Corporate-/seed_charlotte.py` | Charlotte competitor data (40+ shops) | Competitor profiles with real research |
| `/home/user/Corporate-/GOVERNANCE.md` | Data collection governance + ethics rules | Scope, data model, ethical rules |
| `/home/user/Corporate-/warehouse/` | DuckDB warehouse: db.py, intel.py, competitors.py, reports.py | Data layer |
| `/home/user/Corporate-/agents/` | 11 agent classes for competitive intelligence | Pricing scout, review harvester, social listener, etc. |

---

## APPENDIX C: DOCTRINE DECISION RULES (Quick Reference)

From `rnd_doctrine.py` Section 6 — APPROVE when:
- [x] The problem is real
- [x] The customer or user value is identifiable
- [x] The opportunity aligns with strategy
- [x] The technical path is plausible
- [x] The learning plan is defined
- [x] The risks are visible
- [x] Success can be measured

STOP, PAUSE, or REFRAME when:
- [!] Customer value is weak or unproven
- [!] Evidence does not support the concept
- [!] Technology maturity is insufficient
- [!] The project consumes more bandwidth than its value justifies
- [!] Assumptions remain vague after repeated cycles

**Red Lines (Section 12):** No projects without defined value. No optimism substituting for validation. No confusing speed with progress. No burying failure. No launching without understanding requirements, trade-offs, and known risks.

---

*This briefing is the operating manual for all 5 agents. Update it as projects advance, stall, or get killed. The doctrine demands knowledge compounds — this document is how we compound it.*
