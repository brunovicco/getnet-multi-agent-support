#!/usr/bin/env python3
"""Offline routing evaluation over a versioned dataset.

Routing quality is the property most likely to regress silently when a rule is added, so it is
measured rather than asserted anecdotally. The script scores the deterministic rule layer, which
is the layer that must work without credentials; the optional LLM classifier is evaluated by
pointing the same dataset at a configured service.

Usage:
    uv run python scripts/run_router_eval.py
    uv run python scripts/run_router_eval.py \\
        --dataset evals/routing_dataset.jsonl --min-accuracy 1.0
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from getnet_support.application.agents.router import RouterAgent  # noqa: E402
from getnet_support.domain.models import AgentName  # noqa: E402

AGENTS = tuple(agent.value for agent in AgentName)


def load_dataset(path: Path) -> tuple[dict[str, str], ...]:
    """Read the JSONL dataset, failing loudly on a malformed line."""
    rows: list[dict[str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"{path}:{number}: invalid JSON ({error})") from error
        if row.get("expected_agent") not in AGENTS:
            raise SystemExit(f"{path}:{number}: unknown expected_agent")
        rows.append(row)
    if not rows:
        raise SystemExit(f"{path}: dataset is empty")
    return tuple(rows)


def main() -> int:
    """Score the rule router and fail the build when accuracy drops below the threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=REPOSITORY_ROOT / "evals" / "routing_dataset.jsonl"
    )
    parser.add_argument("--min-accuracy", type=float, default=1.0)
    arguments = parser.parse_args()

    dataset = load_dataset(arguments.dataset)
    router = RouterAgent()
    confusion: Counter[tuple[str, str]] = Counter()
    by_kind: Counter[str] = Counter()
    by_kind_correct: Counter[str] = Counter()
    failures: list[tuple[str, str, str, float]] = []

    for row in dataset:
        decision = router.route_with_rules(row["message"])
        expected = row["expected_agent"]
        actual = decision.agent.value
        confusion[(expected, actual)] += 1
        kind = row.get("kind", "unknown")
        by_kind[kind] += 1
        if expected == actual:
            by_kind_correct[kind] += 1
        else:
            failures.append((row["message"], expected, actual, decision.confidence))

    total = len(dataset)
    correct = sum(count for (expected, actual), count in confusion.items() if expected == actual)
    accuracy = correct / total

    print(f"cases: {total}")
    print(f"routing accuracy: {accuracy:.3f}")
    for kind in sorted(by_kind):
        print(f"  {kind}: {by_kind_correct[kind]}/{by_kind[kind]}")

    print("\nper-agent precision / recall")
    for agent in AGENTS:
        predicted = sum(count for (_, actual), count in confusion.items() if actual == agent)
        supported = sum(count for (expected, _), count in confusion.items() if expected == agent)
        hits = confusion[(agent, agent)]
        precision = hits / predicted if predicted else 0.0
        recall = hits / supported if supported else 0.0
        print(f"  {agent:<11} precision={precision:.3f} recall={recall:.3f} support={supported}")

    print("\nconfusion matrix (expected -> actual)")
    header = " " * 13 + "".join(f"{agent:>12}" for agent in AGENTS)
    print(header)
    for expected in AGENTS:
        cells = "".join(f"{confusion[(expected, actual)]:>12}" for actual in AGENTS)
        print(f"{expected:<13}{cells}")

    if failures:
        print("\nfailures")
        for message, expected, actual, confidence in failures:
            print(
                f"  expected={expected:<11} actual={actual:<11} conf={confidence:.2f} :: {message}"
            )

    if accuracy < arguments.min_accuracy:
        print(f"\nFAIL: accuracy {accuracy:.3f} is below the {arguments.min_accuracy:.3f} gate")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
