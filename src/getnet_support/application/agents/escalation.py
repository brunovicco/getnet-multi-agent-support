"""Safe human-handoff behavior with an explicit, observable protocol."""

from hashlib import sha256

from getnet_support.application.language import detect_language, translate
from getnet_support.domain.models import AgentName, AgentResult, RouteName


class EscalationAgent:
    """Return a consistent, bilingual response when automation should stop."""

    def handle(self, *, reason: str, message: str | None = None) -> AgentResult:
        """Create a handoff without leaking internal or customer data."""
        language = detect_language(message) if message else "en"
        key = "escalation_default"
        if "sensitive-data" in reason:
            key = "escalation_sensitive"
        elif "unsupported-action" in reason:
            key = "escalation_unsupported_action"
        reference = _handoff_reference(reason)
        channels = translate("escalation_channels", language, reference=reference)
        return AgentResult(
            answer=f"{translate(key, language)} {channels}",
            agent=AgentName.ESCALATION,
            route=RouteName.HUMAN_HANDOFF,
            handoff_required=True,
        )


def _handoff_reference(reason: str) -> str:
    """Derive a short, stable reference so a handoff can be correlated in logs and in a CRM."""
    return f"HO-{sha256(reason.encode()).hexdigest()[:8].upper()}"
