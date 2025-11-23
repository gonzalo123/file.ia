import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from modules.prompts import MAIN_SYSTEM_PROMPT, SPARTAN_PROMPT

def test_prompts_exist():
    assert MAIN_SYSTEM_PROMPT is not None
    assert len(MAIN_SYSTEM_PROMPT) > 0
    
    assert SPARTAN_PROMPT is not None
    assert len(SPARTAN_PROMPT) > 0

def test_main_system_prompt_content():
    assert "intelligent orchestrator agent" in MAIN_SYSTEM_PROMPT
    assert "Response Format" in MAIN_SYSTEM_PROMPT

def test_spartan_prompt_content():
    assert "Remove emojis" in SPARTAN_PROMPT
    assert "cognitive reconstruction" in SPARTAN_PROMPT
