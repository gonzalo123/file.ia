import logging
import re
import shutil
from functools import wraps
from pathlib import Path
from typing import Any, List, Callable

import chainlit as cl
import jwt
from botocore.config import Config
from botocore.exceptions import ClientError
from strands import Agent
from strands.agent import SlidingWindowConversationManager
from strands.hooks import (
    HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent)
from strands.models import BedrockModel
from strands.types.exceptions import ContextWindowOverflowException
from strands_tools import calculator, current_time, think

from settings import Models, MIME_MAP

logger = logging.getLogger(__name__)


def get_question_from_message(message: cl.Message):
    content_blocks = None
    if message.elements:
        content_blocks = get_content_blocks_from_message(message)

    if content_blocks:
        content_blocks.append({"text": message.content or "Write a summary of the document"})
        question = content_blocks
    else:
        question = message.content

    return question


def get_content_blocks_from_message(message: cl.Message):
    docs = [f for f in message.elements if f.type == "file" and f.mime in MIME_MAP]
    content_blocks = []

    for doc in docs:
        file = Path(doc.path)
        file_bytes = file.read_bytes()
        shutil.rmtree(file.parent)

        content_blocks.append({
            "document": {
                "name": sanitize_filename(doc.name),
                "format": MIME_MAP[doc.mime],
                "source": {"bytes": file_bytes}
            }
        })

    return content_blocks


def sanitize_filename(name: str) -> str:
    # Remove invalid characters (allow alphanumeric, whitespace, hyphens, parentheses, square brackets)
    name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '', name)
    # Replace multiple whitespaces with single whitespace
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def stream_to_step(tool_name: str):
    """
    Decorator to capture streaming output from async generator tools and send to Chainlit Step.

    Follows Chainlit's official pattern for streaming LLM outputs.

    Args:
        tool_name: Name of the tool (used to find the corresponding Step)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the Step for this tool if it exists
            step: cl.Step = cl.user_session.get(f"step_{tool_name}")

            accumulated_content = ""

            # Call the original async generator function
            async for event in func(*args, **kwargs):
                # Extract delta.text if available (similar to OpenAI's delta.content pattern)
                if isinstance(event, dict) and 'delta' in event:
                    delta = event['delta']
                    if isinstance(delta, dict) and 'text' in delta:
                        text_content = delta['text']

                        # Stream the output of the step (following Chainlit's official pattern)
                        if text_content and step:
                            await step.stream_token(text_content)
                            accumulated_content += text_content

                # Always yield the original event for the agent to consume
                yield event

            # Update the Step with final content
            if step:
                step.output = accumulated_content if accumulated_content else "✓ Completed"
                await step.update()

        return wrapper

    return decorator


class LoggingHooks(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    async def before_tool(self, event: BeforeToolCallEvent) -> None:
        step = cl.Step(
            name=f"{event.tool_use['name']}",
            type="tool",
        )
        await step.send()
        cl.user_session.set(f"step_{event.tool_use['name']}", step)
        logger.debug(f"Request started for {event.tool_use['name']}")

    async def after_tool(self, event: AfterToolCallEvent) -> None:
        step: cl.Step = cl.user_session.get(f"step_{event.tool_use['name']}")
        if step:
            # Keep the step visible with final content instead of removing it
            await step.update()
        logger.debug(f"Request completed for {event.tool_use['name']}")


def auth_callback(headers: dict, secret, jwt_algorithm) -> Any:
    if headers.get("x-user-jwt"):
        jwt_token = headers.get("x-user-jwt")
        try:
            decoded_payload = jwt.decode(jwt_token, secret, algorithms=[jwt_algorithm])
            user_info = decoded_payload['user_info']
            logger.info(f"Authenticated user: {user_info['display_name']} ({user_info['userid']})")
            user = cl.User(
                identifier=user_info['userid'],
                display_name=user_info['display_name'],
                metadata={"role": 'user', "provider": "header"})
            cl.user = user
            return user
        except jwt.ExpiredSignatureError:
            cl.logger.error("Token has expired.")
            return None


def get_orchestrator_tools() -> List[Any]:
    from tools.weather.agent import weather_assistant

    tools = [
        current_time,
        calculator,
        think,
        weather_assistant
    ]

    return tools


def get_agent(
        system_prompt: str,
        model: str = Models.CLAUDE_45,
        tools: List[Any] = [],
        hooks: List[HookProvider] = [],
        temperature: float = 0.3,
        llm_read_timeout: int = 300,
        llm_connect_timeout: int = 60,
        llm_max_attempts: int = 10,
        maximum_messages_to_keep: int = 30,
        should_truncate_results: bool = True,
):
    return Agent(
        system_prompt=system_prompt,
        model=BedrockModel(
            model_id=model,
            temperature=temperature,
            boto_client_config=Config(
                read_timeout=llm_read_timeout,
                connect_timeout=llm_connect_timeout,
                retries={'max_attempts': llm_max_attempts}
            )
        ),
        conversation_manager=SlidingWindowConversationManager(
            window_size=maximum_messages_to_keep,
            should_truncate_results=should_truncate_results,
        ),
        tools=tools,
        hooks=hooks
    )


async def process_user_task(agent: Agent, question: Any, debug: bool):
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": question})
    msg = cl.Message(content="")
    await msg.send()

    final_question = question
    if debug and isinstance(question, str):
        extra = (f"If there is any error in any tool during agent execution, "
                 f"explain the error so I can fix it.")
        final_question = f"{question}\n{extra}"
    try:
        async for event in agent.stream_async(final_question):
            if "data" in event:
                await msg.stream_token(str(event["data"]))
            elif "message" in event:
                await msg.stream_token("\n")
                message_history.append(event["message"])
    except ContextWindowOverflowException:
        await msg.stream_token(
            "\n\n⚠️ **Error:** The file is too large for the model to process. Please try a smaller file.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException':
            await msg.stream_token(f"\n\n⚠️ **Error:** Validation error from Bedrock: {e}")
        else:
            await msg.stream_token(f"\n\n⚠️ **Error:** An unexpected error occurred: {e}")
    except Exception as e:
        await msg.stream_token(f"\n\n⚠️ **Error:** An unexpected error occurred: {e}")

    await msg.update()
