# Evaluation and observability

## Principle

Every component that makes a judgement is measured against a versioned dataset, and the metric that
gates merges is the one that fails loudest in production: sending the merchant to the wrong agent,
or citing a source that does not support the answer.

## Implemented today

| What | Where | Gate |
| --- | --- | --- |
| Routing accuracy, per-agent precision/recall, confusion matrix | `scripts/run_router_eval.py` over `evals/routing_dataset.jsonl` (39 cases) | fails below 1.00 in CI |
| Bilingual scenario regression | `tests/unit/application/test_router.py` | pytest |
| Grounding rejection of off-topic evidence | `tests/unit/application/test_knowledge_grounding.py` | pytest |
| Corpus hygiene | `tests/unit/adapters/test_cleaning.py` | pytest |
| Cross-customer isolation | `tests/unit/adapters/test_customer_tools.py` | pytest |

The dataset separates `challenge`, `paraphrase`, and `guardrail` cases and reports accuracy per
kind, because a router can score well overall while failing every paraphrase — which is exactly the
failure mode that reaches real merchants.

## Calibration backlog

These constants currently carry reviewed defaults and are the next things to calibrate against
labelled data rather than judgement:

| Constant | Value | Calibrate with |
| --- | --- | --- |
| `ROUTING_CONFIDENCE_THRESHOLD` | 0.60 | escalation-rate versus routing-error curve on the routing dataset |
| `CLASSIFIER_CONSULT_BELOW_CONFIDENCE` | 0.75 | share of traffic sent to the provider versus routing accuracy gained |
| `MINIMUM_CLASSIFIER_CONFIDENCE` | 0.60 | accuracy of classifier answers by reported confidence bucket |
| `MINIMUM_RETRIEVAL_SCORE` | 0.08 (noise floor) | precision@1 on a labelled query→source set |
| `MINIMUM_TERM_COVERAGE` | 0.20 | groundedness versus unnecessary-escalation trade-off |
| `CURATED_PREFERENCE_RATIO` | 0.65 | answer-quality review of curated versus scraped selections |

Routing confidence is a monotonic heuristic, not a probability. It should not be presented as
calibrated until the reliability curve above exists.

## Retrieval metrics to add

Recall@K, Precision@K, and MRR against a labelled query-to-source set; stale-document and
empty-retrieval rates; and an adversarial slice of pages containing prompt-injection instructions,
asserting that no instruction inside retrieved content changes behaviour.

## Generation metrics to add

Groundedness, citation entailment, unsupported-claim rate, and refusal quality when evidence is
insufficient — each scored on the same dataset with and without the optional LLM enabled, so the
model's contribution is measurable rather than assumed.

## Support-agent metrics

Correct tool selection and argument accuracy, unauthorized cross-user access rate (target: zero,
already asserted in tests), fact consistency with tool output, automated-resolution rate, and
appropriate-handoff rate.

## Operational metrics

Routing specifically: classifier consult rate (share of messages below the consult threshold),
classifier fallback rate split by cause via `decision_source`, and classifier latency as its own
series — routing sits on the request path, so a provider slowdown shows up as p95 chat latency
before it shows up anywhere else.

p50/p95/p99 end-to-end and per-tool latency; error, timeout, and tool-failure rates; escalation
rate split by cause (guardrail, low confidence, insufficient evidence, unknown user); retrieval
result counts and zero-result rate; token and model cost when an LLM adapter is enabled.

## Observability

Each request emits `router_decision` and `agent_execution` as structured JSON with the trace ID,
selected and secondary agent, reason, confidence, guardrail flag, latency, tool-call and retrieval
counts, and handoff state. Prompts, answers, secrets, and customer record contents are never
logged; `user_id` appears only as a namespaced SHA-256 `user_reference_hash`, which is
pseudonymization and therefore keeps the same access and retention protections as other
operational metadata.

Production path: application metadata → OpenTelemetry → OTLP collector → Datadog, Grafana Tempo, or
another backend. Offline evaluation gates pull requests; production traffic feeds privacy-safe
online aggregates plus sampled, access-controlled human review.
