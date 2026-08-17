"""Safe human-handoff behavior with an explicit, observable protocol."""

from dataclasses import replace
from hashlib import sha256

from getnet_support.application.language import detect_language, translate
from getnet_support.domain.models import AgentName, AgentResult, RouteName


class EscalationAgent:
    """Return a consistent, bilingual response when automation should stop."""

    def handle(
        self,
        *,
        reason: str,
        message: str | None = None,
        reference_seed: str | None = None,
    ) -> AgentResult:
        """Create a handoff without leaking internal or customer data."""
        language = detect_language(message) if message else "en"
        key = "escalation_default"
        if "sensitive-data" in reason:
            key = "escalation_sensitive"
        elif "unsupported-action" in reason:
            key = "escalation_unsupported_action"
        reference = handoff_reference(reference_seed or f"{reason}:{message or ''}")
        channels = translate("escalation_channels", language, reference=reference)
        return AgentResult(
            answer=f"{translate(key, language)} {channels}",
            agent=AgentName.ESCALATION,
            route=RouteName.HUMAN_HANDOFF,
            handoff_required=True,
            handoff_reference=reference,
        )


def attach_handoff_reference(
    result: AgentResult,
    *,
    message: str,
    reference_seed: str,
) -> AgentResult:
    """Attach one request-scoped reference to a handoff returned by any specialized agent."""
    if not result.handoff_required or result.handoff_reference is not None:
        return result
    language = detect_language(message)
    reference = handoff_reference(reference_seed)
    channels = translate("escalation_channels", language, reference=reference)
    return replace(
        result,
        answer=f"{result.answer} {channels}".strip(),
        handoff_reference=reference,
    )


def handoff_reference(reference_seed: str) -> str:
    """Derive a stable request reference suitable for metadata-only correlation."""
    return f"HO-{sha256(reference_seed.encode()).hexdigest()[:8].upper()}"
