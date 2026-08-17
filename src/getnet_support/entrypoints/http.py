"""FastAPI composition root and HTTP routes."""

from uuid import uuid4

from fastapi import FastAPI, Response

from getnet_support import __version__
from getnet_support.adapters.events import StructlogEventSink
from getnet_support.adapters.rag.corpus import DEFAULT_GETNET_CORPUS
from getnet_support.adapters.rag.retriever import LocalTfidfRetriever
from getnet_support.adapters.repositories.fake_customer_repository import FakeCustomerRepository
from getnet_support.adapters.settings import Settings
from getnet_support.adapters.tools.customer import CustomerProfileTool
from getnet_support.adapters.tools.terminal import TerminalStatusTool
from getnet_support.adapters.tools.transactions import RecentTransactionsTool
from getnet_support.adapters.tools.web_search import WebSearchTool
from getnet_support.application.agents.customer_support import CustomerSupportAgent
from getnet_support.application.agents.escalation import EscalationAgent
from getnet_support.application.agents.knowledge import KnowledgeAgent
from getnet_support.application.agents.router import RouterAgent
from getnet_support.application.orchestrator import SupportOrchestrator
from getnet_support.entrypoints.logging import (
    bind_correlation_id,
    clear_request_context,
    configure_logging,
)
from getnet_support.entrypoints.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ServiceIndexResponse,
)


def build_orchestrator(settings: Settings) -> SupportOrchestrator:
    """Wire concrete adapters to framework-free application ports."""
    repository = FakeCustomerRepository()
    knowledge = KnowledgeAgent(
        LocalTfidfRetriever(DEFAULT_GETNET_CORPUS),
        WebSearchTool(
            provider=settings.web_search_provider,
            api_key=settings.web_search_api_key,
        ),
    )
    support = CustomerSupportAgent(
        CustomerProfileTool(repository),
        RecentTransactionsTool(repository),
        TerminalStatusTool(repository),
    )
    return SupportOrchestrator(
        router=RouterAgent(),
        knowledge=knowledge,
        support=support,
        escalation=EscalationAgent(),
        events=StructlogEventSink(),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated FastAPI application for runtime or tests."""
    resolved_settings = settings or Settings()
    configure_logging(
        service=resolved_settings.service_name,
        environment=resolved_settings.app_env,
        version=__version__,
    )
    orchestrator = build_orchestrator(resolved_settings)
    application = FastAPI(
        title="Getnet Multi-Agent Support",
        version=__version__,
        description="Explicitly orchestrated support agents with grounded local RAG.",
    )

    @application.get("/", response_model=ServiceIndexResponse)
    async def index() -> ServiceIndexResponse:
        return ServiceIndexResponse(
            service=resolved_settings.service_name,
            version=__version__,
        )

    @application.get("/favicon.ico", include_in_schema=False, status_code=204)
    async def favicon() -> Response:
        return Response(status_code=204)

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            service=resolved_settings.service_name,
        )

    @application.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        trace_id = uuid4().hex
        bind_correlation_id(trace_id)
        try:
            result = await orchestrator.chat(
                message=request.message,
                user_id=request.user_id,
                trace_id=trace_id,
            )
            return ChatResponse.from_domain(result)
        finally:
            clear_request_context()

    return application


app = create_app()
