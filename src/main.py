import asyncio
import logging
from typing import Dict, Optional

import chainlit as cl
from botocore.exceptions import ClientError
from strands.types.exceptions import ContextWindowOverflowException

from modules.cl import (
    auth_callback, get_agent, get_orchestrator_tools, LoggingHooks, get_content_blocks_from_message)
from modules.prompts import MAIN_SYSTEM_PROMPT
from settings import (
    ENVIRONMENT, SECRET,
    JWT_ALGORITHM, FAKE_USER, DEBUG)

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level='INFO',
    datefmt='%d/%m/%Y %X')

logger = logging.getLogger(__name__)


@cl.header_auth_callback
def header_auth_callback(headers: Dict) -> Optional[cl.User]:
    if ENVIRONMENT == 'local' and FAKE_USER:
        user = cl.User(
            identifier=FAKE_USER,
            display_name=FAKE_USER,
            metadata={"role": 'admin', "provider": "local"})
        cl.User = user
        return user
    else:
        return auth_callback(headers=headers, secret=SECRET, jwt_algorithm=JWT_ALGORITHM)


@cl.on_chat_start
async def start_chat():
    cl.user_session.set("should_stop", False)
    cl.user_session.set("current_task", None)
    cl.user_session.set("files", {})

    agent = get_agent(
        system_prompt=MAIN_SYSTEM_PROMPT,
        hooks=[LoggingHooks()],
        tools=get_orchestrator_tools()
    )
    cl.user_session.set("agent", agent)

    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}],
    )


@cl.on_chat_end
async def on_chat_end():
    current_task = cl.user_session.get("current_task")
    if current_task and not current_task.done():
        current_task.cancel()

    task = cl.user_session.get("task")
    if task and not task.done():
        task.cancel()


@cl.on_message
async def handle_message(message: cl.Message):
    agent = cl.user_session.get("agent")

    message_history = cl.user_session.get("message_history")
    files = cl.user_session.get("files", {})

    if message.elements:
        content_blocks = get_content_blocks_from_message(message)

        if content_blocks:
            content_blocks.append({"text": message.content})
            user_message = {
                "role": "user",
                "content": content_blocks
            }
            message_history.append(user_message)
            cl.user_session.set("files", files)
            question = content_blocks
        else:
            message_history.append({"role": "user", "content": message.content})
            question = message.content
    else:
        message_history.append({"role": "user", "content": message.content})
        question = message.content

    async def user_task(debug):
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

    task = asyncio.create_task(user_task(DEBUG))
    cl.user_session.set("task", task)
    cl.user_session.set("conversation_history", message_history)
    try:
        await task
    except asyncio.CancelledError:
        logger.info("User task was cancelled.")
