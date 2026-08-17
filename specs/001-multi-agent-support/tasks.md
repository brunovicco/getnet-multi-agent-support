# Tasks 001

Each task lists the requirements it satisfies and the test that proves it. Order reflects the
dependency chain, not the elapsed time.

| # | Task | Requirements | Verified by |
| --- | --- | --- | --- |
| 1 | Domain contracts (route decision, agent result, chunks, customer records) | REQ-N3 | `tests/unit/test_package.py`, `scripts/validate_architecture.py` |
| 2 | Typed ports for retrieval, search, generation, classification, tools | REQ-R4, REQ-S1 | `tests/unit/application/test_agents.py` |
| 3 | Rule router with prefix and co-occurrence matchers | REQ-R1, REQ-R2 | `tests/unit/application/test_router.py` |
| 4 | Guardrail rules and low-confidence escalation | REQ-R3, REQ-R5, REQ-E1 | `test_guardrail_decisions_are_flagged_for_the_orchestrator` |
| 5 | Optional LLM classifier with rule fallback | REQ-R4 | `test_rules_are_used_when_the_classifier_fails` |
| 6 | Corpus ingestion, cleaning, and validated artifact | REQ-K5 | `tests/unit/adapters/test_cleaning.py`, `tests/integration/test_rag_pipeline.py` |
| 7 | Retrieval with score and term-coverage gates | REQ-K1, REQ-K2 | `tests/unit/application/test_knowledge_grounding.py` |
| 8 | Web-search port with explicit unavailable result | REQ-K3 | `tests/unit/adapters/test_web_search.py` |
| 9 | Customer tools scoped by `user_id` | REQ-S1, REQ-S2, REQ-S3 | `tests/unit/adapters/test_customer_tools.py` |
| 10 | Escalation agent with handoff reference | REQ-E1 | `tests/unit/application/test_agents.py` |
| 11 | Bilingual response catalogue | REQ-L1 | `tests/unit/application/test_language.py` |
| 12 | Orchestrator, including the agent sequence | REQ-R6, REQ-O1 | `tests/unit/application/test_orchestrator.py` |
| 13 | FastAPI boundary, health, validation | REQ-A1, REQ-A2, REQ-A3 | `tests/integration/test_api.py` |
| 14 | Metadata-only structured logging | REQ-O1, REQ-O2 | `tests/unit/test_logging.py` |
| 15 | Offline routing evaluation and CI gate | REQ-R7 | `scripts/run_router_eval.py` |
| 16 | Docker image and compose file | REQ-N2 | `Dockerfile`, `docker-compose.yml` |

## Open items

* Calibrate `MINIMUM_RETRIEVAL_SCORE` and `CURATED_PREFERENCE_RATIO` against a labelled retrieval
  dataset instead of the current reviewed defaults.
* Extend the evaluation dataset with adversarial prompt-injection pages.
* Replace the fake customer repository with resilient CRM, payments, and terminal adapters.
