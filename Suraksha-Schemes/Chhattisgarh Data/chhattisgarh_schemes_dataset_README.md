# Chhattisgarh Schemes Canonical CSV

**Snapshot:** 2026-09-30 | **Research/build date:** 2026-10-09

## Included files

- `chhattisgarh_schemes_canonical_asof_2026-09-30.csv` — 616 candidate records, 39 columns, UTF-8 with BOM for spreadsheet compatibility.
- `chhattisgarh_schemes_implementation_plan.md` — detailed research, verification, RAG and QA plan.

## Counts and limitations

The current CSV has 82 state-level rows and 534 central-level rows. It is an initial candidate inventory, **not a claim of completeness or approval-ready eligibility data**. 578 rows are `unverified_seed`. Central government ownership is not evidence that every Chhattisgarh citizen qualifies. Budgeted programmes and public services are labeled separately from personal application schemes. Superseded and legacy candidates must not be recommended as current.

The source README for the Hugging Face repository reports a July 2026 collection of 4,693 schemes, while the locally supplied JSON snapshot is smaller (2,066 records). A production release should ingest and reconcile the current repository `Schemes.csv` revision.

## Main fields

`scheme_id`, `slug`, `name`, `description`, `level`, `state`, `ministry`, `department`, `category`, `beneficiary_type`, `eligibility_text`, structured eligibility fields, `exclusions`, `benefits`, `application_mode`, `application_process`, `documents_required`, `faqs`, `myscheme_url`, `official_external_url`, `apply_url`, `source_provenance`, `source_last_updated`, `source_scraped_at`, `last_verified_at`, `verification_status`, `target_state`, `record_type`, `applicability_to_chhattisgarh`, `as_of_date`, and `data_quality_notes`.

Structured eligibility values use JSON arrays in CSV text cells for multi-value fields. Empty or `[]` means unknown/not parsed unless a source explicitly says otherwise; it must not be interpreted as “no restrictions.” The controlled verification status values are described in the implementation plan.

## Recommended filter before citizen-facing retrieval

Only use records marked `verified_active` for affirmative eligibility recommendations. This initial snapshot has no row that should be treated as production-certified solely because it appears in the file. Show other records only as candidates with source links and an explicit verification warning.

## Key source links

- Hugging Face README: https://huggingface.co/datasets/smartduketech/indian-government-schemes-2025/blob/main/README.md
- Chhattisgarh CM Helpline scheme directory: https://cmhelpline.cg.gov.in/Home/Schemes
- Chhattisgarh Finance 2026–27 Key Highlights: https://finance.cg.gov.in/budget_doc/2026-2027/key_Highlight/Key_Highlight-E.pdf
- Chhattisgarh Food Department: https://fcs.cg.gov.in/PlanScheme_Hn.aspx
- Chhattisgarh Tribal/SC Department: https://tribal.cg.gov.in/departmental-plans
- PMAY-U 2.0: https://pmaymis.gov.in/pmaymis2_2024/PmayUrban.aspx
- VB–G RAM G status notice: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2290638&lang=1&reg=3

## Attribution

The source repository README states CC BY 4.0 and attributes the underlying scheme data to SmartDuke Technologies with original source myScheme. Retain required attribution and verify licensing before redistribution. See the implementation plan for scope, source hierarchy and next steps.
