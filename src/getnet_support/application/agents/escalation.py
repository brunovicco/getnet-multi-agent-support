"""Safe human-handoff behavior."""

from getnet_support.domain.models import AgentName, AgentResult, RouteName


class EscalationAgent:
    """Return a consistent response when automation should stop."""

    def handle(self, *, reason: str) -> AgentResult:
        """Create a handoff without leaking internal or customer data."""
        return AgentResult(
            answer=(
                "I could not resolve this request confidently and safely. "
                "Human support is recommended."
            ),
            agent=AgentName.ESCALATION,
            route=RouteName.HUMAN_HANDOFF,
            handoff_required=True,
        )
