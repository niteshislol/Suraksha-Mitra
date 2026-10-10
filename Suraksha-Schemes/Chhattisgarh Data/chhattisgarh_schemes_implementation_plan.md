# Chhattisgarh Government Schemes Dataset — Detailed Implementation Plan

**Snapshot requested:** schemes announced/active or potentially relevant to citizens residing in Chhattisgarh through **30 September 2026**.  
**Dataset built:** 9 October 2026.  
**Primary output:** `chhattisgarh_schemes_canonical_asof_2026-09-30.csv`  
**Intended use:** scheme discovery, eligibility triage, and retrieval-augmented generation (RAG), after the review gates below are completed.

## 1. Executive summary and readiness decision

The current CSV is a **research seed and implementation baseline, not a certified exhaustive inventory**. It contains **616 records** in a single 39-column canonical schema: **82 Chhattisgarh state-level candidates and 534 central-level candidates**. It includes the supplied registry, selected additions from official Chhattisgarh and central-government sources, source provenance, controlled verification status, and a historical/superseded distinction for the old rural employment scheme.

Two constraints prevent describing it as “all schemes” or deploying it directly for citizen-facing eligibility decisions:

1. The supplied local JSON registry contains 2,066 records according to its own structure/commentary, whereas the Hugging Face README describes a July 2026 collection of 4,693 records. The local snapshot therefore does not match the latest README-reported inventory. Obtain and ingest the repository's current `Schemes.csv` before calling the national seed coverage complete.
2. **578 records remain `unverified_seed`**; most central records are candidates whose currentness, state applicability, live application window, and exact exclusion rules still need primary-source review. A record present in a dataset is not evidence that a scheme remains open, applies to Chhattisgarh, or applies to an individual citizen.

The next milestone should be **verification and completeness research**, not model training or production recommendations. In particular, keep programmes/budget lines (for example, road infrastructure or a mission allocation) distinct from schemes that an individual can apply to.

## 2. Scope and inclusion rules

### Geographic and institutional scope

Include all of these, but distinguish them clearly:

- **State schemes:** schemes owned/funded by the Government of Chhattisgarh and limited to qualifying residents, households, workers, farmers, students, or locations in the state.
- **Central schemes applicable in the state:** Central Sector and Centrally Sponsored schemes for which Chhattisgarh residents, institutions, or eligible projects may qualify. Central ownership does **not** mean every citizen qualifies.
- **Converged or co-funded programmes:** keep the central programme record and the Chhattisgarh implementation/benefit record separate when the state adds eligibility, top-ups, package rules, or a different application route.
- **Programmes and public services:** preserve them for discovery when useful, but mark records that are project-, institution-, habitation-, or service-based and do not have a universal individual application.
- **Legacy, closed, or replaced schemes:** retain for historical queries, benefit-payment disputes, and successor mapping, but never expose as current without a separate current-status check.

### Snapshot date

`as_of_date=2026-09-30` is the requested knowledge cut-off. `source_scraped_at` and `last_verified_at` represent when the data was collected/reviewed, not when the government last amended the scheme. Keep `source_last_updated` blank if the page does not provide a trustworthy update date; do not infer it from a crawl date or search-engine crawl label.

### Citizen-facing safety rule

Only records that pass the production verification gate can be used for a definitive statement such as “you are eligible” or “applications are open.” All other records must be expressed as candidates and direct users to the relevant government verification channel.

## 3. Source hierarchy and research map

Use the highest available source in this order:

1. **Current scheme notification, operational guidelines, government order, or amendment** published by the competent ministry/department.
2. **Official scheme portal** maintained by the implementing department.
3. **Official Chhattisgarh department or district portal** describing state implementation.
4. **myScheme** for discovery and standardized scheme detail; cross-check eligibility, exclusions, and application URLs on the implementing source.
5. **Official state budget, budget speech, department annual report, or PIB** for evidence of a budget provision, launch, statutory change, or policy status. A budget amount is not an individual benefit amount.
6. District notices, public service centres, or secondary sources may point researchers to the responsible office, but must not be the final authority for eligibility if a primary source exists.

### Priority source register

| Source | URL | What to collect | Important constraint |
|---|---|---|---|
| Hugging Face dataset repository / README | https://huggingface.co/datasets/smartduketech/indian-government-schemes-2025/blob/main/README.md | Baseline national scheme inventory and field definitions | README reports a July 2026 collection of 4,693 records and explicitly warns users to verify changing eligibility/benefit details. Attribute according to CC BY 4.0. |
| myScheme | https://www.myscheme.gov.in/ | Candidate scheme pages, eligibility, benefits, application URLs | Treat as a discovery/index layer, not sole proof that a live application window is open. |
| Chhattisgarh CM Helpline — Schemes | https://cmhelpline.cg.gov.in/Home/Schemes | Department-by-department citizen scheme discovery | Page itself says final eligibility/application decisions remain subject to the concerned scheme rules and department. |
| Chhattisgarh Finance — 2026–27 Key Highlights | https://finance.cg.gov.in/budget_doc/2026-2027/key_Highlight/Key_Highlight-E.pdf | Current-year budget-listed programme names and allocations | Budget allocation is not a person-level benefit; map every line to its scheme rule and nodal department. |
| Chhattisgarh Food Department — schemes | https://fcs.cg.gov.in/PlanScheme_Hn.aspx | PDS, rice procurement, ration-card and food-distribution programmes | Some content mixes historical marketing years and may have old quantities/rates; require a dated 2026 order or live system confirmation. |
| Chhattisgarh Food Department — English | https://fcs.cg.gov.in/PlanScheme_En.aspx | English cross-check of food-scheme names | Some page content is old; use for discovery, not current rates without corroboration. |
| Chhattisgarh tribal / SC department | https://tribal.cg.gov.in/departmental-plans | SC/ST educational, welfare and economic assistance | Separate student schemes, scholarships, residential-school entry, financial assistance, and institution grants. Check current academic year rules. |
| Chhattisgarh Sewa Setu / e-District discovery | https://cgstate.gov.in/ | State service routes and application form discovery | Verify the production host before adding an `apply_url`; do not copy a UAT host into citizen-facing links. |
| VB–G RAM G official PIB release | https://www.pib.gov.in/PressReleasePage.aspx?PRID=2290638&lang=1&reg=3 | Rural employment scheme status change from 1 July 2026 | Current status must reflect applicable law/date, not the legacy dataset's scheme name. |
| VB–G RAM G official FAQ | https://www.pib.gov.in/FaqDetails.aspx?ModuleId=4&NoteId=158511&lang=1&reg=3 | Effective date, statutory entitlement, change from MGNREGA | Verify Chhattisgarh operational forms and rules with the state notification. |
| PMAY-U 2.0 official portal | https://pmaymis.gov.in/pmaymis2_2024/PmayUrban.aspx | Current urban housing verticals and core eligibility | Keep distinct from the legacy PMAY-U phase; check state/local-body route and vertical-specific conditions. |
| PMAY-G eligibility flow | https://pmayg.nic.in/netiayHome/questions.html | Rural housing deprivation/eligibility screening | A screening result is not a sanction; confirm survey/list/priority and state implementation. |
| PM Fasal Bima Yojana | https://pmfby.gov.in/ | Crop, season, notified-area and enrollment information | Every crop season has time-sensitive notifications/deadlines. |
| Jal Jeevan Mission | https://jaljeevanmission.gov.in/ | Rural tap-water mission and service definitions | Generally service/infrastructure based; do not represent as universal cash aid. |
| PMGSY | https://pmgsy.nic.in/ | Rural-road project scheme | Infrastructure/project programme, not an individual application scheme. |
| PM Ujjwala Yojana | https://www.pmuy.gov.in/about.html | Adult-woman rule, eligible household categories, current connection allocation | Check the latest allocation and distributor steps. |
| National Health Authority / PM-JAY | https://nha.gov.in/PM-JAY and https://beneficiary.nha.gov.in/ | Health-beneficiary check, covered hospitalization, authorized workflow | Keep central PM-JAY distinct from Chhattisgarh's state health-assurance programme until official convergence and package rules are mapped. |
| PM Surya Ghar | https://pmsuryaghar.gov.in/ | Residential rooftop-solar eligibility and application steps | Confirm DISCOM readiness, current subsidy rate, installation and net-metering steps. |

### Department inventory to complete

Use the CM Helpline department directory and state government directory to ensure every department is queried, then create a source-coverage checklist by department. At minimum cover: Agriculture and Farmer Welfare; Food/Civil Supplies; Tribal/SC/OBC/Minority Welfare; Labour and Building/Other Construction Workers; Women and Child Development; Health and Family Welfare; School Education; Higher Education; Skill Development and Employment; Rural Development/Panchayat; Urban Administration; Housing; Energy/DISCOM; Revenue and Disaster Management; Social Welfare/Pensions; Fisheries/Livestock; Industries/MSME; Transport; Culture/Tourism; Sports/Youth; and relevant district administrations. For each department, inspect scheme pages, citizen service portals, current-year rules, archived orders, and application notices.

## 4. Canonical data model and field contract

### Required base fields

The CSV carries the requested fields and additional review fields. Treat the following as the canonical contract:

| Field | Contract |
|---|---|
| `scheme_id` | Stable, globally unique identifier. Do not recycle IDs when names change. Suggested prefixes: `CG-ST-` for Chhattisgarh-owned state records; `IN-CEN-` for centrally owned records. |
| `slug` | Stable URL-safe key; preserve a former slug as an alias in provenance if the source renames a scheme. |
| `name` | Official display name. Store local-language name/alias in a future `name_hi`/`aliases` field rather than concatenating it into the official name. |
| `description` | Neutral summary of purpose, not persuasive or political language. |
| `level` | Controlled value: `state` or `central`. If a future release needs Local Body or district schemes, extend the enumeration deliberately and document it. |
| `state` | `Chhattisgarh` for state-level records; blank for central-level records. Do not use this field to store the ministry. |
| `ministry` | Union ministry for central records. Blank for state-owned schemes when the source describes only a state department. |
| `department` | Implementing/nodal department, not a list of tags. Track the source that established this. |
| `category` | Multi-label topic taxonomy; normalize to approved categories, keep original tags in an alias/raw field if needed. |
| `beneficiary_type` | Plain-language intended beneficiaries (for example, eligible farmers, urban EWS households, registered construction workers). |
| `eligibility_text` | Source-aligned human-readable eligibility, with restrictions and exceptions preserved. |
| `eligibility_age_min`, `eligibility_age_max` | Integer years only when explicitly stated. Blank means unknown/not stated, not “no age limit.” |
| `eligibility_gender` | Normalize to `female`, `male`, `all`, or blank/unknown. Do not infer gender from the scheme name alone. |
| `eligibility_caste` | JSON array such as `["SC","ST"]`; keep uncategorized or unparsed as `[]`/unknown and preserve the raw text. |
| `eligibility_income_max` | Integer INR per year, only when the source explicitly defines an upper bound and the family/person basis is clear. |
| `eligibility_residence` | `rural`, `urban`, `both`, or blank/unknown. |
| `eligibility_state` | JSON array such as `["Chhattisgarh"]`, `["All"]`, or `[]` when not established. `[]` must not be interpreted as ineligible. |
| `eligibility_disability`, `eligibility_bpl` | Boolean-like controlled values. Prefer `true`, `false`, `unknown`; never use `false` merely because the text omits a condition. |
| `exclusions` | Explicit disqualifiers, overlap rules, government employee/taxpayer exclusions, prior-housing benefits, and other restrictions. |
| `benefits` | Person-level assistance or service outcome. Never put a whole budget allocation in the same semantic slot without labeling it as a programme allocation. |
| `application_mode`, `application_process`, `documents_required` | Only current source-supported steps. Avoid saying “online” when the portal is only informational. |
| `faqs` | Preserve useful official question-answer pairs, after deduplication and correction of obvious encoding artifacts. |
| `myscheme_url`, `official_external_url`, `apply_url` | Separate directory/detail page, authoritative implementing source, and direct application route. `apply_url` must be reachable and active-tested before citizen use. |
| `source_provenance` | JSON object/array containing source URLs, source type, source title, review timestamp, facts supported, conflicts, and notes. One URL alone is not adequate provenance for multi-source claims. |
| `source_last_updated` | Date shown by the source itself, if present. Keep blank otherwise. |
| `source_scraped_at` | Timestamp of this collection run. Preserve original collection time separately if known. |
| `last_verified_at` | Last human/source verification timestamp, distinct from `source_last_updated`. Update only after actual review. |
| `verification_status` | Controlled status enum defined below. |
| `target_state`, `record_type`, `applicability_to_chhattisgarh`, `as_of_date`, `data_quality_notes` | Scope/record-type metadata, applicability decision, snapshot cutoff, and human-readable limitations. |

### Controlled `verification_status`

The current CSV uses a controlled 10-value subset, with detail kept in `source_provenance` and `data_quality_notes`:

- `unverified_seed` — imported candidate; not yet checked against a current primary source.
- `official_source_rules_pending` — official source located; full current eligibility/benefit/application rules still need validation.
- `official_source_application_window_pending` — core source exists but current registration window/route is unconfirmed.
- `official_source_state_implementation_pending` — central scheme exists but Chhattisgarh rollout, local-body route, or convergence remains unconfirmed.
- `official_source_beneficiary_rules_pending` — official portal linked, but a live beneficiary-level determination is required.
- `seasonal_rules_pending` — crop, district, year/season, deadline, or notified rules must be rechecked each cycle.
- `budget_only` — a budget allocation supports programme existence/planned spending only; it does not establish applicant-level entitlement.
- `programme_not_individual_entitlement` — programme/service/infrastructure entry with component-specific, local, or institutional implementation, not a universal personal application.
- `legacy_phase_candidate` — historical or possibly replaced phase; must not be recommended for new applicants until successor mapping is verified.
- `superseded` — primary evidence confirms a legal or programme replacement; retain for history only.

Add `verified_active` only after all production verification gates pass. Never treat any status above other than `verified_active` as an affirmative eligibility decision.

## 5. End-to-end implementation workflow

### Phase 0 — Freeze inputs, license and audit the baseline

1. Preserve the supplied `gov_myscheme_data.json` unchanged and compute its SHA-256 hash.
2. Download the exact `Schemes.csv` revision from the Hugging Face repository, record the commit/revision hash, retrieval time, row count and file hash, and reconcile why the README's 4,693-record inventory differs from the supplied JSON's 2,066 records.
3. Record the dataset license/attribution in the repository README and keep the original source schema and field mapping in version control.
4. Create a one-time baseline audit with file row counts, field names, duplicate IDs, duplicate slugs, missing URLs, empty fields, encoding artifacts and sample source links.

**Exit gate:** every source input has a stable local copy, hash, retrieval date, license note, row count and mapping record.

### Phase 1 — Discover the complete Chhattisgarh scheme universe

1. Use the State budget's major-scheme list as a **discovery checklist**, not as a complete scheme list or eligibility source.
2. Search the CM Helpline scheme directory and each department's official pages for schemes, programmes, sub-schemes, scholarships, pensions, grants, utility subsidies, insurance, seasonal benefits, and service entitlements.
3. For Tribal/SC/OBC/Minority Welfare and Labour, collect the detailed scheme rules, official notices, application forms, academic-year notices and closure/renewal dates. These portfolios often contain multiple sub-schemes not summarized in a general portal.
4. Crawl district-specific notifications when eligibility depends on notified areas, tribal/PVTG habitation, crop, town, local body, or district. Store geography as an explicit predicate and a list of areas, not as narrative-only text.
5. Add an inventory row even if details are missing, but use `official_source_rules_pending` / `unverified_seed` and a review task rather than guessing.

**Exit gate:** every relevant department has a source coverage record: `searched`, `no scheme listing found`, `listing found but details absent`, or `review complete`. Absence from a page is not proof a scheme does not exist.

### Phase 2 — Ingest, parse and normalize

1. Parse HTML pages, PDFs, tables, forms and notices with a source-aware scraper. Keep the retrieved raw content and original URL alongside extracted text. Use HTML parsing where possible; for PDFs store both text extraction and page images for layout-dependent tables.
2. Preserve source language. Keep original Hindi/English scheme title and content in raw/alias fields, and create a reviewed English summary as a separate representation.
3. Normalize whitespace, HTML entities and encoding without changing legal terms, caste categories, eligibility negation, dates, amounts, or exceptions.
4. Map source-specific field names to the canonical contract using explicit source maps; do not use uncontrolled fuzzy column inference in production.
5. Extract structured eligibility with conservative rules. LLM-extracted age/income/gender/caste/residence values must carry evidence spans/source quotes and be validated against the exact source paragraph.
6. Represent unknown distinctly from false/no limit; preserve original `eligibility_text` even when structured parsing is successful.
7. Convert all amount fields only when currency, period and recipient unit are clear. Do not mistake annual budget allocation, grant ceilings, insurance cover, per-household payment, per-month subsidy and per-application grant for one another.

**Exit gate:** each transformed row can be traced back to the raw source and an explicit source-to-canonical mapping.

### Phase 3 — Identity resolution and deduplication

1. Use exact normalized title + jurisdiction + scheme owner as the first duplicate key.
2. Build alias tables for alternate English spellings, Hindi transliterations, abbreviations, old names, current names, and portal slugs.
3. Never merge schemes solely because the name is similar. For example, a central PM-JAY entry and the Chhattisgarh state health-assurance entry must remain separate until state convergence, packages, funding and beneficiary rules are established.
4. Preserve renamed predecessors with `legacy_phase_candidate` or `superseded`, and link successors through `successor_scheme_id` in a future schema extension. Do not overwrite the historical rules with the new scheme's rules.
5. Merge duplicate source pages into the same record's provenance, but retain individual source URLs and source dates.

**Exit gate:** unique `scheme_id`, no accidental cross-state merge, duplicate report reviewed, all renamed/merged rows auditable.

### Phase 4 — Primary-source verification and temporal status

For every citizen-applicable record, verify all of the following before setting `verified_active`:

- Official title and scheme owner/nodal department.
- Status as of 30 September 2026: active, not accepting new applications, seasonal/closed, discontinued, superseded, or unclear.
- Beneficiary class, geography, residency/domicile, age, gender, income, caste/category, occupation, land/house/asset conditions, family constraints and exclusions.
- Benefit amount/unit/period; whether money is direct benefit, reimbursement, insurance cover, service delivery or institution/project allocation.
- Documents and certificates, including whether originals, uploads, e-KYC, bank/DBT or a scheme-specific registration are required.
- Direct application URL and whether the form is open; offline/CSC/Gram Panchayat routes if applicable.
- Source last-updated date, source-scraped date and human last-verified date.
- Conflict notes for discrepancies between myScheme and the latest implementing authority rule.

Use two-person review for high-impact benefits (housing, pensions, cash transfers, health cover, employment guarantee, crop insurance and food entitlement) and legal/status transitions. If no current rule can be found, keep the record unverified; do not infer from old article pages.

**Known temporal example:** PIB states that VB–G RAM G took effect from 1 July 2026 and the MGNREGA Act stood repealed from that date. The legacy MGNREGA record is therefore retained as `superseded`; it must not be returned as the current rural employment guarantee as of the requested September cutoff. Confirm operational details/forms through Chhattisgarh notices before giving a step-by-step state application route.

**Exit gate:** every live, citizen-facing scheme has a primary current rule, dates, exclusions, source-grounded benefit and tested application channel.

### Phase 5 — Eligibility schema and matching engine

1. Separate **hard constraints** from **ranking preferences**. State, age, sex/gender restrictions, statutory beneficiary category, notified geography, current/seasonal application window and required registration are usually hard constraints.
2. Use three-valued logic (`true`, `false`, `unknown`) for conditions. Missing income or age data cannot be interpreted as satisfying the rule.
3. Model household-level versus individual-level eligibility explicitly. Housing, PDS, PM-JAY and many pensions cannot safely be assessed from one person's profile alone.
4. Add fields in a later migration for `eligibility_scope` (individual/household/institution/project), `geography_ids`, `occupation_codes`, `landholding`, `housing_status`, `ration_card_category`, `worker_registration`, `crop_season`, `application_window_start/end`, `scheme_start/end`, `successor_scheme_id`, and `rule_version`.
5. A rules engine should evaluate deterministic constraints first; the LLM explains the result and asks for missing facts. It must not determine eligibility from similarity alone.
6. Return result labels such as **likely match**, **possible match—details missing**, **not a match based on stated rule**, and **status/window needs confirmation**. Avoid guaranteed eligibility or approval language.

### Phase 6 — RAG corpus and citizen experience

1. Generate one retrieval document per scheme plus smaller source-grounded chunks for eligibility, benefits, exclusions, application process, documents and FAQs.
2. Attach metadata: `scheme_id`, `level`, `state`, `ministry`, `department`, categories, geography, `verification_status`, `as_of_date`, `source_last_updated`, source authority, and `record_type`.
3. Use hybrid retrieval (keyword + vector) because official scheme names, acronyms, caste categories, legal terms, and exact benefit amounts require lexical precision. Add Hindi/English alias search.
4. Filter out `superseded`, `legacy_phase_candidate`, `unverified_seed` and `budget_only` records from definitive recommendations by default. They can be returned only in a research/history view with warnings.
5. Never chunk across different schemes. A retriever should return the source for every claim about eligibility, amount, deadline, document, or application URL.
6. Prefer exact official URLs for click-through. Before each answer, check freshness fields and surface when the official source is older than policy thresholds or application windows are seasonal.
7. Use an LLM such as Gemini 3.1 Pro for source-grounded summarization, multilingual explanation and question clarification—not as the source of legal rules or current deadlines. Prompt it to cite `scheme_id` and source URLs for every substantive recommendation and to say “not established from current official sources” when evidence is missing.
8. Do not ask citizens to submit Aadhaar numbers, bank account numbers, caste certificates or other sensitive records to the model. Ask only for the minimum facts needed to triage; route formal documentation to official portals.

### Phase 7 — QA, evaluation, and release

Automated release checks:

- CSV can be opened with UTF-8 BOM and standard CSV parsers; embedded newlines, commas and quotes round-trip correctly.
- `scheme_id` unique and required base columns present.
- `level` is valid; `state='Chhattisgarh'` for state records and blank for central records.
- Enum values are valid; unknown eligibility is not encoded as false or unrestricted.
- Every candidate has a provenance object; every `verified_active` record has at least one current primary rule source and a direct application/service route where applicable.
- Every external link is HTTP-tested on a schedule; UAT, login-only, dead, shortened and third-party application URLs are not labeled as an official direct application route.
- Benefits and income ceilings are numeric/unit validated; allocations are explicitly labelled as programme allocations.
- Duplicate report, changed-name report, supersession report and stale-source report have zero unreviewed critical cases.
- Hindi and English names/aliases resolve to the same `scheme_id` where appropriate.

Human evaluation set:

- At least 100 representative scenarios across farmers, landless workers, women, children/students, construction/unorganised workers, SC/ST/OBC/minority beneficiaries, senior citizens, persons with disabilities, low-income urban households, rural households, and general residents.
- Include negative cases: non-Chhattisgarh state schemes, expired/seasonal applications, a budget allocation mistaken for benefit amount, missing age/income, households previously allotted housing, and legacy MGNREGA queries after 1 July 2026.
- Measure precision of eligibility recommendations, source citation correctness, critical fact accuracy, no-unsupported-claim rate, stale-link rate, and refusal/clarification behavior on incomplete profile data.

Suggested go-live thresholds: 100% of recommended results have a current official source; 100% of deadlines and amounts in tests match the cited rule; zero superseded records in current recommendations; at least 95% critical-field coverage among records marked `verified_active`; and at least 95% of sampled application links resolve to the intended government endpoint. Treat these as release gates, not claims about the current CSV.

## 6. Recommended work prioritization

### P0 — Current high-impact citizen entitlements

Mahtari Vandan; Krishak Unnati; Deendayal Upadhyaya Bhumihin Krishi Majdoor Kalyan; Mukhya Mantri Khadyaan Sahayata/PDS; Shaheed Veer Narayan Singh Ayushman Swasthya; PMAY-G and PMAY-U 2.0; PM-JAY convergence; rural employment guarantee after 1 July 2026; crop insurance; PM-KISAN; PMUY; pension/social assistance; scholarships and current academic-year schemes; eligible agricultural electricity benefits. Verify benefit unit, exclusions and live registration route.

### P1 — State department portfolios with many small schemes

Construction and unorganised workers, cleaning/sanitation workers, workers' child scholarships and maternity aid; SC/ST/OBC/minority scholarships and coaching; girls' education/transport/cycle schemes; women/child nutrition; food-distribution sub-schemes; disability/senior-citizen benefits; artisan/startup/MSME programmes; solar/irrigation; fisheries and livestock.

### P2 — Service and infrastructure programmes

Jal Jeevan Mission, PMGSY, Samagra Shiksha, NHM, PM-JANMAN, and state/local development allocations. Convert these into the citizen-service subcomponents that can be acted on, while retaining the parent mission as contextual metadata.

### P3 — Legacy and low-confidence long tail

Old state schemes from the supplied registry, entries with missing official application route, and schemes whose currentness cannot be established. Keep visible in the internal review queue; exclude from positive matches until verified.

## 7. Deliverables for a production-grade release

1. `schemes_canonical.csv` — row-per-scheme canonical export, versioned by snapshot date.
2. `schemes_raw_sources/` — immutable downloaded source pages/PDFs with hashes and retrieval metadata.
3. `scheme_source_register.csv` — one row per evidence source, not just one provenance blob per scheme.
4. `scheme_review_queue.csv` — owner, priority, status, reviewer, due date, unresolved questions and final decision for every unverified record.
5. `scheme_change_log.csv` — old/new values, source, effective date, detection time and reviewer for amendments/renames/closures.
6. `data_dictionary.md` — field definitions, types, null rules, enums and examples.
7. `ingestion_pipeline/` — deterministic download, parse, mapping, deduplication, temporal checks and CSV generation scripts.
8. `evaluation/` — versioned eligibility test cases, expected result/source, and regression report.
9. `release_manifest.json` — snapshot date, software revision, input hashes, record counts, verification-status counts, source coverage, quality metrics and license attribution.

## 8. Immediate next actions

1. Replace the old supplied registry with the current Hugging Face `Schemes.csv` revision and reconcile count/field differences; retain this 616-row CSV as the initial migration baseline.
2. Create a complete state-department source inventory from the Chhattisgarh CM Helpline directory and department portals. Record which departments and scheme categories have been searched.
3. Verify the P0 state schemes against current 2026 rules and live applicant portals, resolving all legacy names and beneficiary overlap rules.
4. Review all 534 central candidates for geographic eligibility, programme type, active status and Chhattisgarh implementation. Do not assume all central records are citizen schemes or apply to all residents.
5. Move records to `verified_active` only after a reviewer signs off on rules, source citations, status, dates and application route. Then ingest only verified current rows into the production eligibility index; retain other statuses in an internal discovery/history index.

## 9. Current CSV limitations to carry forward

- The national baseline is based on the supplied 2,066-record local snapshot, not yet the README-reported 4,693-record current CSV.
- Current source-research additions are intentionally conservative and many are labeled as candidates because authoritative pages did not establish all exact rules in this pass.
- Official Food Department pages establish useful scheme names and historical entitlements, but parts of the page include old dates/amounts; do not represent those figures as current without a fresh government order.
- Budget allocations in the 2026–27 highlight are programme-level budget figures, not amounts paid to an individual.
- Several Chhattisgarh state scheme names in the input are historical or may have successor schemes; do not expose `unverified_seed` or `legacy_phase_candidate` as active recommendations.
- `source_last_updated` is blank where a source-provided date was not verified. This is preferable to fabricating a last-updated date.

**Dataset attribution:** SmartDuke Technologies, *Indian Government Schemes Dataset 2026*, Hugging Face, CC BY 4.0, based on myScheme as described in the dataset README. The uploaded local registry is treated as the supplied input snapshot; provenance is retained at row level. Verify licensing and retain attribution if distributing a derived dataset.
