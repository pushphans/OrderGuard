import uuid
from typing import Literal

from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from orderguard_ai.ai.core.state import AgentState
from orderguard_ai.ai.core.llm import get_llm
from orderguard_ai.ai.core.tools import cart_tools
from orderguard_ai.ai.core.tools import order_tools
from orderguard_ai.ai.workflow.prompts import SUPERVISOR_PROMPT
from orderguard_ai.ai.workflow.prompts import CART_AGENT_PROMPT
from orderguard_ai.ai.workflow.prompts import ORDERS_AGENT_PROMPT
from orderguard_ai.core.product_client import ProductClient


FINISH = "FINISH"


class SupervisorDecision(BaseModel):
    next: Literal["cart_agent", "orders_agent", FINISH] = Field(
        description="Which agent should handle the user's current request, or FINISH when the task is complete."
    )


def build_supervisor_workflow(
    db: AsyncSession,
    user_id: uuid.UUID,
    client: ProductClient
):
    """Build the supervisor workflow for a single caller.

    A supervisor LLM routes the conversation between a cart agent and an
    orders agent (each a ReAct tool-calling subgraph) and ends the run when
    the task is complete.
    """
    llm = get_llm()

    cart_agent = create_react_agent(
        llm,
        cart_tools(db, user_id, client),
        prompt=CART_AGENT_PROMPT
    )

    orders_agent = create_react_agent(
        llm,
        order_tools(db, user_id, client),
        prompt=ORDERS_AGENT_PROMPT
    )

    supervisor_llm = llm.with_structured_output(SupervisorDecision)

    async def supervisor(state: AgentState) -> Command:
        decision = await supervisor_llm.ainvoke(
            [SystemMessage(content=SUPERVISOR_PROMPT), *state["messages"]]
        )

        target = decision.next

        if target == FINISH:
            return Command(goto=END, update={"context": ["FINISH"]})

        return Command(goto=target, update={"context": [f"routed_to_{target}"]})

    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("cart_agent", cart_agent)
    graph.add_node("orders_agent", orders_agent)

    graph.add_edge(START, "supervisor")
    graph.add_edge("cart_agent", "supervisor")
    graph.add_edge("orders_agent", "supervisor")

    return graph.compile()
