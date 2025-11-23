import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock chainlit before importing main
mock_cl = MagicMock()
sys.modules["chainlit"] = mock_cl

# Configure decorators to return the function so we can test them
mock_cl.header_auth_callback = lambda f: f
mock_cl.on_chat_start = lambda f: f
mock_cl.on_chat_end = lambda f: f
mock_cl.on_message = lambda f: f

# Now import main
from main import header_auth_callback, start_chat, on_chat_end, handle_message

@patch('main.ENVIRONMENT', 'local')
@patch('main.FAKE_USER', 'test_user')
def test_header_auth_callback_local():
    # Setup User mock
    mock_user = MagicMock()
    # Create a fresh mock for the class to avoid pollution from previous tests
    mock_user_cls = MagicMock(return_value=mock_user)
    mock_cl.User = mock_user_cls
    
    headers = {}
    user = header_auth_callback(headers)
    
    mock_user_cls.assert_called_with(
        identifier='test_user',
        display_name='test_user',
        metadata={"role": 'admin', "provider": "local"}
    )
    assert user == mock_user

@patch('main.ENVIRONMENT', 'production')
@patch('main.auth_callback')
@patch('main.SECRET', 'test_secret')
@patch('main.JWT_ALGORITHM', 'HS256')
def test_header_auth_callback_prod(mock_auth_callback):
    headers = {'x-user-jwt': 'token'}
    header_auth_callback(headers)
    
    mock_auth_callback.assert_called_with(
        headers=headers,
        secret='test_secret',
        jwt_algorithm='HS256'
    )

@pytest.mark.asyncio
@patch('main.get_agent')
@patch('main.get_orchestrator_tools')
async def test_start_chat(mock_get_tools, mock_get_agent):
    # Setup user_session mock
    mock_session = MagicMock()
    mock_cl.user_session = mock_session
    
    await start_chat()
    
    assert mock_session.set.call_count >= 4
    mock_session.set.assert_any_call("should_stop", False)
    mock_session.set.assert_any_call("current_task", None)
    mock_session.set.assert_any_call("agent", mock_get_agent.return_value)

@pytest.mark.asyncio
async def test_on_chat_end():
    # Setup user_session mock
    mock_session = MagicMock()
    mock_cl.user_session = mock_session
    
    mock_task = MagicMock()
    mock_task.done.return_value = False
    
    mock_session.get.side_effect = [mock_task, mock_task] # current_task, task
    
    await on_chat_end()
    
    assert mock_task.cancel.call_count == 2

@pytest.mark.asyncio
@patch('main.get_question_from_message')
@patch('main.process_user_task')
@patch('main.asyncio.create_task')
async def test_handle_message(mock_create_task, mock_process_task, mock_get_question):
    # Setup user_session mock
    mock_session = MagicMock()
    mock_cl.user_session = mock_session
    
    message = MagicMock()
    mock_agent = MagicMock()
    mock_history = []
    
    def get_side_effect(key):
        if key == "agent": return mock_agent
        if key == "message_history": return mock_history
        return None
        
    mock_session.get.side_effect = get_side_effect
    
    mock_get_question.return_value = "test question"
    
    # Mock the task to be awaitable
    # Use a Future which is awaitable
    loop = asyncio.get_running_loop()
    mock_task = loop.create_future()
    mock_task.set_result(None)
    
    mock_create_task.return_value = mock_task
    
    await handle_message(message)
    
    assert len(mock_history) == 1
    assert mock_history[0] == {"role": "user", "content": "test question"}
    
    mock_create_task.assert_called_once()
    mock_session.set.assert_any_call("task", mock_task)
    mock_session.set.assert_any_call("conversation_history", mock_history)
