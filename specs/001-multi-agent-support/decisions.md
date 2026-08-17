# Decisions 001

## D1 — Explicit orchestration instead of LangGraph or LangChain

**Chosen:** a direct, typed call graph in `SupportOrchestrator`.
**Rejected:** a workflow framework.
**Why:** at this scope a framework adds a runtime, a state model, and a debugging surface without
removing any real complexity, and it obscures exactly what an evaluator needs to see: which agent
ran, why, and with what data. The orchestrator is one file with no hidden control flow.
**Revisit when:** durable execution, retries across process restarts, or human-in-the-loop pauses
become requirements.

## D2 — Rules first, model second, in the router

**Chosen:** deterministic rules as the default and permanent fallback; an optional LLM classifier
that only breaks non-guardrail ties below the reviewed rule-confidence threshold.
**Rejected:** LLM-only routing, and rules-only routing.
**Why:** LLM-only routing cannot run without credentials, is non-reproducible in CI, and adds
latency and cost to a decision that is often trivial. Rules-only routing overfits to the phrasing
of whoever wrote them. Spending the model only on the ambiguous tail gives a working
credential-free path and a generalizing path, with the guardrails never delegated.
**Cost accepted:** two implementations of the same contract must be evaluated by the same dataset.

## D3 — TF-IDF instead of embeddings

**Chosen:** a dependency-free lexical index over ~20 reviewed chunks.
**Rejected:** a vector database.
**Why:** at this corpus size a vector store is infrastructure without measurable retrieval gain,
and it would make the service dependent on a provider at startup. The port keeps the swap cheap.
**Cost accepted:** no semantic matching, which is why a term-coverage gate is required and why
bilingual chunks are stored explicitly rather than relying on cross-lingual embeddings.

## D4 — Bilingual curated chunks instead of translation at query time

**Chosen:** each reviewed claim stored in both Portuguese and English, citing the same source.
**Rejected:** translating the query, or translating the answer with a model.
**Why:** a lexical index does not bridge languages, and query translation would add a model call to
the credential-free path. Storing both keeps retrieval deterministic and keeps citations exact.

## D5 — Escalation as a first-class agent

**Chosen:** a fourth agent owning every stop condition (low confidence, guardrail, unknown user,
insufficient evidence).
**Rejected:** returning an error, or letting each agent write its own refusal.
**Why:** a single policy owner means one place to change handoff wording and one orchestrator seam
to attach the trace-derived reference even when a specialized agent detects the stop condition.
The reference is emitted as safe metadata and the final route remains observable for measuring the
automated-resolution rate.

## D6 — Sequences triggered by intent composition, not score proximity

**Chosen:** a sequence requires a support-incident signal plus a product-topic term.
**Rejected:** running the runner-up agent whenever its score is close.
**Why:** device words are simultaneously product words, so score proximity fires on ordinary
incidents and appends marketing text to an operational answer. Composition is precise and
explainable to an evaluator.
