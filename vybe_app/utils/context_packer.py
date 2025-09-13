"""
Context packing utilities to keep orchestrator inputs lean while preserving meaning.

Strategies implemented:
- Keep the latest system prompt; drop older/duplicate system prompts
- Keep the most recent user/assistant turns up to a character budget
- Optionally strip overly long blocks (code/logs) to placeholders

Note: This is a character-based approximation. Token-aware packing can be
added later by integrating a tokenizer for the specific model family.
"""
from typing import List, Dict


def _strip_heavy_blocks(text: str, max_block_chars: int = 2000) -> str:
    """Collapse very large blocks (e.g., logs/code) to placeholders."""
    if not text:
        return text
    # Simple heuristic: if a line exceeds threshold repeatedly, collapse
    if len(text) <= max_block_chars:
        return text
    # Keep the head and tail, elide the middle
    head = text[: max_block_chars // 2]
    tail = text[-max_block_chars // 2 :]
    return f"{head}\n\n[... {len(text) - len(head) - len(tail)} chars omitted ...]\n\n{tail}"


def pack_messages(messages: List[Dict], max_chars: int = 24000) -> List[Dict]:
    """
    Pack chat messages into a compact list within a character budget.

    - Keeps the last system message only
    - Iterates from the most recent to oldest user/assistant messages until budget
    - Strips heavy blocks to reduce size
    """
    if not messages:
        return []

    # Find the latest system message (if any)
    last_system = None
    for m in reversed(messages):
        if m.get("role") == "system":
            last_system = {"role": "system", "content": _strip_heavy_blocks(m.get("content", ""), 4000)}
            break

    # Iterate from newest to oldest for user/assistant content
    packed_rev: List[Dict] = []
    current_chars = len(last_system.get("content", "")) if last_system else 0
    budget = max(max_chars, 1000)

    for m in reversed(messages):
        role = m.get("role")
        if role == "system":
            # Only include the latest system once; skip others
            continue
        content = _strip_heavy_blocks(m.get("content", ""), 4000)
        # Ensure we always include the most recent user message even if large
        projected = current_chars + len(content)
        if not packed_rev:
            packed_rev.append({"role": role, "content": content})
            current_chars = projected
            continue
        if projected > budget:
            # Stop when budget exceeded
            break
        packed_rev.append({"role": role, "content": content})
        current_chars = projected

    packed = list(reversed(packed_rev))
    if last_system:
        return [last_system] + packed
    return packed


def clamp_text(text: str, max_chars: int = 24000) -> str:
    """Clamp long text to a safe size with an omission marker."""
    if not isinstance(text, str):
        return text
    if len(text) <= max_chars:
        return text
    head = text[: max_chars - 400]
    return f"{head}\n\n[... {len(text) - len(head)} chars omitted ...]"


