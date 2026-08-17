# Testing strategy

## What is being defended

The risk in a multi-agent support system is not a crash. It is a fluent, well-formatted, wrongly
sourced answer: the right-looking product page cited for the wrong product, another customer's
settlement date, or a confident reply where the honest answer is "a human should handle this". The
test suite is organized around those failures rather than around code coverage.

## Layers

| Layer | Scope | Doubles | Speed |
| --- | --- | --- | --- |
| Unit — domain and application | routing rules, grounding gates, tool selection, language, merge logic | in-memory stubs implementing the ports | milliseconds |
| Unit — adapters | Tavily and OpenAI HTTP contracts, corpus validation, cleaning, retrieval math | `httpx.MockTransport`, temporary files | milliseconds |
| Integration | HTML → chunks → artifact → index → retrieval → grounded answer; `/chat`, `/health`, validation | real objects end to end, no network | under a second |
| Offline evaluation | routing accuracy over a versioned dataset | none — the real rule router | under a second |

Every test runs with no credentials and no network. That is a design requirement, not a
convenience: a suite that needs a provider key stops being run.

## Comprehensive integration testing of the orchestration

The orchestration is tested as a graph, not as a set of functions.

1. **Every branch is exercised.** Knowledge/RAG, knowledge/web-search, support/tools,
   escalation/handoff, and the agent sequence each have an end-to-end test asserting the observable
   contract: `agent`, `route`, `sources`, `handoff_required`, and the emitted events.
2. **Both languages, every scenario.** The ten scenarios from the brief are asserted in Portuguese
   and English. A system for Brazilian merchants that is only tested in English is untested.
3. **Negative grounding.** A stub retriever returns an off-topic chunk *above* the similarity
   threshold; the expected outcome is escalation, not an answer. This is the regression test for
   the real defect where a crediário question was answered from the antecipação article.
4. **Tenant isolation.** A second fake customer exists solely so cross-customer reads fail. Terminal
   lookups resolve only through the requesting user's assigned terminal, and an unknown user gets a
   handoff that discloses nothing.
5. **Privacy of telemetry.** Orchestration tests assert that no event contains the raw `user_id`,
   the message, or the answer, and that the pseudonymous reference is stable within a request.
6. **Provider failure paths.** Both the search and generation adapters are driven through
   `MockTransport` with HTTP errors, malformed bodies, and schema violations; each must degrade to
   the deterministic local path rather than propagate.

## Evaluation as a test

`scripts/run_router_eval.py` scores the rule router against `evals/routing_dataset.jsonl` and fails
below the accuracy gate. It runs in the quality gate and in CI, so a new routing rule that fixes one
phrasing and breaks three others cannot merge silently. See `docs/EVALUATION.md`.

## Running

```bash
uv run pytest                              # full suite with coverage gate
uv run pytest tests/unit -q                # fast inner loop
uv run python scripts/run_router_eval.py   # routing accuracy and confusion matrix
uv run python scripts/quality_gate.py      # lint, format, architecture, types, tests, eval, security
```

## What is deliberately not tested here

Live provider behaviour (contract tests use recorded shapes), load and latency under concurrency,
and the quality of an LLM-generated answer — the last belongs to the online/offline evaluation loop
in `docs/EVALUATION.md`, not to a unit test with a fixed expected string.
