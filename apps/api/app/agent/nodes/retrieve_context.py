"""Read-only destination context retrieval node."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.agent.state import AgentState, trip_request_from_state
from app.rag.schemas import RetrievalRequest
from app.rag.service import RAGRetriever


def build_retrieve_context_node(
    rag_retriever: RAGRetriever | None = None,
) -> Callable[[AgentState], dict[str, object]]:
    """Build a non-blocking retrieve_context node for the planning graph."""

    async def _retrieve(state: AgentState) -> dict[str, object]:
        if rag_retriever is None:
            return {}

        trip_request = trip_request_from_state(state)
        if trip_request is None or not trip_request.destination:
            return {
                "retrieved_context": None,
                "retrieved_context_formatted": None,
            }

        try:
            request = RetrievalRequest(
                query=f"{trip_request.destination} travel planning background",
                destination=trip_request.destination,
                top_k=5,
            )
            context = await rag_retriever.retrieve(request)
            return {
                "retrieved_context": context.model_dump(mode="json"),
                "retrieved_context_formatted": rag_retriever.format_context(context),
            }
        except Exception:
            return {
                "retrieved_context": None,
                "retrieved_context_formatted": None,
            }

    def retrieve_context(state: AgentState) -> dict[str, object]:
        if rag_retriever is None:
            return {}
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_retrieve(state))

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, _retrieve(state))
            return future.result()

    return retrieve_context
