"""
GINA System Prompt - Personality and behavior definition.

This prompt is automatically injected into every GINA chat conversation.
It defines GINA's personality, capabilities, constraints, and behavior.

Loads from: workers/local_core/gina_personality_prompt.md
"""
from pathlib import Path

# Load prompt from markdown file
_PROMPT_FILE = Path(__file__).parent / "gina_personality_prompt.md"

if _PROMPT_FILE.exists():
    # Read markdown file, skip front matter if present
    content = _PROMPT_FILE.read_text(encoding="utf-8")
    # Remove YAML front matter if present (lines between --- markers at start)
    lines = content.split("\n")
    if lines[0].strip() == "---":
        # Find second ---
        end_idx = 1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i + 1
                break
        content = "\n".join(lines[end_idx:])
    GINA_SYSTEM_PROMPT = content.strip()
else:
    # Fallback to embedded prompt if file doesn't exist
    GINA_SYSTEM_PROMPT = """
You are GINA (Governance, Intelligence, Navigation Assistant) running inside the QiOS local environment.

You are NOT a generic chatbot. You are the ops brain for a local cognitive operating system.

[Fallback prompt - gina_personality_prompt.md not found]
""".strip()
