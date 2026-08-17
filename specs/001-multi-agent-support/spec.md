# Spec 001 — Multi-agent Getnet support system

## Problem

A Getnet merchant sends one free-text message, in Portuguese or English, that may be a public
product question, a question about their own account, a general-information question, or a request
the system must not fulfil. The system must decide what kind of request it is and answer it with
evidence, or hand it to a human — without ever inventing a product fact or a customer fact.

## Users and scope

* Merchant (end user), writing in Portuguese or English through a single HTTP endpoint.
* Human support operator, who receives escalations with a correlation reference.
* Evaluator/operator, who needs the routing decision and its reason to be observable.

Out of scope: authentication, any state-changing operation on the customer's account, and multi-turn
conversation memory.

## Functional requirements

### Routing

* **REQ-R1** The system MUST classify every message into exactly one primary agent: knowledge,
  support, or escalation.
* **REQ-R2** The system MUST route with equal accuracy in Portuguese and English, including
  paraphrases that were not used to author the rules.
* **REQ-R3** WHEN routing confidence is below `ROUTING_CONFIDENCE_THRESHOLD` (0.60), the system
  MUST escalate instead of guessing an agent.
* **REQ-R4** The system MUST work with no model credentials configured. A model-backed classifier
  MAY take precedence when configured, and MUST fall back to the deterministic rules on any
  provider failure.
* **REQ-R5** Guardrail decisions (sensitive data, unsupported actions) MUST NOT be delegated to a
  model classifier.
* **REQ-R6** WHEN a message contains both a customer-specific incident and a public product topic,
  the system MUST execute an agent sequence and merge both results into one response.
* **REQ-R7** Routing accuracy MUST be measured against a versioned dataset, not asserted
  anecdotally.

### Knowledge

* **REQ-K1** Getnet product questions MUST be answered only from retrieved evidence, with the
  official source URL attached to the response.
* **REQ-K2** WHEN retrieval evidence does not meet both the score gate and the term-coverage gate,
  the system MUST escalate rather than answer.
* **REQ-K3** General-information and time-sensitive questions MUST use the web-search port; when it
  is unconfigured the system MUST say so explicitly instead of fabricating an answer.
* **REQ-K4** Retrieved content MUST be treated as untrusted data; instructions inside it MUST NOT
  be followed.
* **REQ-K5** The indexed corpus MUST NOT contain cross-page navigation, contact, or footer text.

### Customer support

* **REQ-S1** Customer facts MUST originate only from typed, customer-scoped tools; no model may
  create them.
* **REQ-S2** A tool MUST NOT accept an arbitrary customer, terminal, or account selector; the
  authenticated `user_id` is the only key.
* **REQ-S3** WHEN the user is unknown, the system MUST hand off without disclosing anything.

### Escalation

* **REQ-E1** Every escalation MUST set `handoff_required=true`, disclose no private data, and carry
  a stable handoff reference for correlation.

### Language

* **REQ-L1** Every agent response MUST be produced in the language of the incoming message.

### API

* **REQ-A1** `POST /chat` MUST accept `{message, user_id}` and return `answer`, `agent`, `route`,
  `sources`, `trace_id`, `confidence`, and `handoff_required`.
* **REQ-A2** Invalid input MUST be rejected at the transport boundary with `422`.
* **REQ-A3** `GET /health` MUST report which optional capabilities are active without calling them.

### Observability

* **REQ-O1** Each request MUST emit routing and execution events with a trace ID, latency, tool
  counts, and handoff state.
* **REQ-O2** Raw `user_id`, message content, and answers MUST NOT be logged.

## Non-functional requirements

* **REQ-N1** Startup MUST perform no provider network calls.
* **REQ-N2** The service MUST build and run with standard Docker commands.
* **REQ-N3** Architecture dependencies MUST point inward: entrypoints → application → domain.

## Acceptance scenarios

All ten scenarios from the challenge brief MUST route and answer correctly **in both Portuguese and
English**. They are encoded in `evals/routing_dataset.jsonl` and in
`tests/unit/application/test_router.py`.

| Scenario | Expected agent | Requirement |
| --- | --- | --- |
| Get Clássica vs Get Smart | knowledge (RAG) | REQ-K1 |
| Weather in Porto Alegre tomorrow | knowledge (web) | REQ-K3 |
| When is yesterday's sale deposited | support | REQ-S1 |
| Bank account needed for Pix | knowledge (RAG) | REQ-K1 |
| Card machine will not connect | support | REQ-S1 |
| How receivables advance works | knowledge (RAG) | REQ-K1 |
| Euro exchange rate today | knowledge (web) | REQ-K3 |
| Transaction decline error | support | REQ-S1 |
| Crediário installments | knowledge (RAG) | REQ-K1, REQ-K2 |
| Sell via WhatsApp with Payment Link | knowledge (RAG) | REQ-K1 |

## Explicit non-goals

Vector database, multi-turn memory, live CRM/payments integrations, and any write operation. Each
has a named seam in `design.md` instead of a partial implementation.
