import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from modules.cl import sanitize_filename, get_question_from_message, get_content_blocks_from_message, auth_callback

def test_sanitize_filename():
    assert sanitize_filename("valid_name.txt") == "valid_name.txt"
    assert sanitize_filename("invalid/name.txt") == "invalidname.txt"
    assert sanitize_filename("name with spaces.txt") == "name with spaces.txt"
    assert sanitize_filename("  multiple   spaces  ") == "multiple spaces"
    assert sanitize_filename("test-file(1).pdf") == "test-file(1).pdf"

def test_get_question_from_message_text_only():
    message = MagicMock()
    message.elements = []
    message.content = "Hello world"
    
    question = get_question_from_message(message)
    assert question == "Hello world"

@patch('modules.cl.get_content_blocks_from_message')
def test_get_question_from_message_with_files(mock_get_blocks):
    message = MagicMock()
    message.elements = [MagicMock()]
    message.content = "Summarize this"
    
    mock_get_blocks.return_value = [{"document": "data"}]
    
    question = get_question_from_message(message)
    
    assert isinstance(question, list)
    assert len(question) == 2
    assert question[0] == {"document": "data"}
    assert question[1] == {"text": "Summarize this"}

@patch('modules.cl.Path')
@patch('modules.cl.shutil.rmtree')
def test_get_content_blocks_from_message(mock_rmtree, mock_path):
    message = MagicMock()
    element = MagicMock()
    element.type = "file"
    element.mime = "application/pdf"
    element.path = "/tmp/test.pdf"
    element.name = "test.pdf"
    message.elements = [element]
    
    # Mock Path behavior
    mock_file = MagicMock()
    mock_file.read_bytes.return_value = b"file_content"
    mock_path.return_value = mock_file
    
    # Mock MIME_MAP in settings (needs to be patched where it's imported)
    with patch('modules.cl.MIME_MAP', {"application/pdf": "pdf"}):
        blocks = get_content_blocks_from_message(message)
        
        assert len(blocks) == 1
        assert blocks[0]["document"]["name"] == "test.pdf"
        assert blocks[0]["document"]["format"] == "pdf"
        assert blocks[0]["document"]["source"]["bytes"] == b"file_content"
        
        mock_rmtree.assert_called_once()

@patch('modules.cl.jwt.decode')
@patch('modules.cl.cl.User')
def test_auth_callback_success(mock_user_cls, mock_jwt_decode):
    headers = {"x-user-jwt": "valid_token"}
    secret = "secret"
    algo = "HS256"
    
    mock_jwt_decode.return_value = {
        "user_info": {
            "userid": "123",
            "display_name": "Test User"
        }
    }
    
    mock_user_instance = MagicMock()
    mock_user_cls.return_value = mock_user_instance
    
    user = auth_callback(headers, secret, algo)
    
    assert user == mock_user_instance
    mock_user_cls.assert_called_with(
        identifier="123",
        display_name="Test User",
        metadata={"role": 'user', "provider": "header"}
    )

@patch('modules.cl.jwt.decode')
def test_auth_callback_expired(mock_jwt_decode):
    import jwt
    headers = {"x-user-jwt": "expired_token"}
    
    mock_jwt_decode.side_effect = jwt.ExpiredSignatureError()
    
    user = auth_callback(headers, "secret", "HS256")
    
    assert user is None
