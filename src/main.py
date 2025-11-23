import asyncio
import logging
from typing import Dict, Optional

import chainlit as cl

from modules.cl import (
    auth_callback, get_agent, get_orchestrator_tools, LoggingHooks, get_question_from_message, process_user_task)
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

    agent = get_agent(
        system_prompt=MAIN_SYSTEM_PROMPT,
        hooks=[LoggingHooks()],
        tools=get_orchestrator_tools()
    )
    cl.user_session.set("agent", agent)
    cl.user_session.set("message_history", [])


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
    task = asyncio.create_task(process_user_task(
        question=get_question_from_message(message),
        debug=DEBUG))
    cl.user_session.set("task", task)
    try:
        await task
    except asyncio.CancelledError:
        logger.info("User task was cancelled.")
