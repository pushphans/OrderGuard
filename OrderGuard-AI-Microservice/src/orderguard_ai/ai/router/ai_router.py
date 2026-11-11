import uuid

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from orderguard_ai.ai.schema.ai_schema import AiChatRequestModel
from orderguard_ai.ai.schema.ai_schema import AiChatResponseModel
from orderguard_ai.ai.workflow.graph import build_supervisor_workflow
from orderguard_ai.auth.utils.current_user_utils import get_user
from orderguard_ai.core.db import get_db
from orderguard_ai.core.limiter import limiter
from orderguard_ai.core.product_client import ProductClient
from orderguard_ai.core.product_client import get_product_client
from fastapi import Depends
from fastapi import Request
from fastapi import status
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter


ai_router = APIRouter(prefix="/ai", tags=["AI"])


@ai_router.post("/chat")
@limiter.limit("10/minute")
async def execute_ai_chat(
    request: Request,
    data : AiChatRequestModel,
    db : AsyncSession = Depends(get_db),
    user_id : uuid.UUID = Depends(get_user),
    client : ProductClient = Depends(get_product_client)
):
    try:
        graph = build_supervisor_workflow(db=db, user_id=user_id, client=client)

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=data.message)]},
            config={"recursion_limit": 50}
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = str(error)
        )

    except GraphRecursionError:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "AI agent run did not converge; please try again"
        )

    except Exception as error:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = str(error)
        )

    answer = "Anything I can help with regarding your cart or orders?"

    for message in reversed(result["messages"]):
        if isinstance(message, AIMessage) and message.content:
            answer = message.content
            break

    return AiChatResponseModel(
        message=answer,
        steps=result.get("context", [])
    )
