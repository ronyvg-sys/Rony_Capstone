"""W4 REFERENCE-ONLY — anthropic_reference.py

Read this. Don't import it. Don't run it in the lab.

The W4 deck Slide 33 calls out three differences between the OpenAI SDK and the
Anthropic SDK. This file is what those three differences look like in actual
code — so when you switch providers in production, you know what changes and
what doesn't.

To use it for real you would need:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

The Anthropic API isn't part of the cohort's required toolchain.
"""
from __future__ import annotations

import json
from anthropic import AsyncAnthropic  # not installed in lab venv on purpose

from src.pipeline.models import Answer, Question


# ─── Difference 1: tool schema is slightly different ────────────────────────
# Anthropic doesn't wrap the schema in {"type": "function", "function": {...}}.
# The schema lives at the top level of each tool entry.
ANSWER_TOOL_ANTHROPIC = {
    "name": "answer_question",
    "description": "Return a structured answer with content, confidence, sources.",
    "input_schema": {  # ← "input_schema" not "parameters"
        "type": "object",
        "properties": {
            "content":    {"type": "string"},
            "confidence": {"type": "number"},
            "sources":    {"type": "array", "items": {"type": "string"}},
        },
        "required": ["content", "confidence", "sources"],
    },
}


async def ask_llm_anthropic(q: Question, model: str = "claude-sonnet-4-20250514") -> Answer:
    """Same shape as our ask_llm, but talking to Claude.

    Three things change vs the OpenAI version (everything else is identical):
      1. The client class is AsyncAnthropic, not AsyncOpenAI.
      2. The method is client.messages.create(), not chat.completions.create().
      3. System prompts are a top-level kwarg, not a message in `messages`.
      4. Tool-use comes back as a content block of type "tool_use", not on
         message.tool_calls.
    """
    client = AsyncAnthropic()

    # Difference 2: client.messages.create instead of chat.completions.create
    resp = await client.messages.create(
        model=model,
        max_tokens=1024,                                  # required by Anthropic
        # Difference 3: system is a top-level param, not a message
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": q.question}],
        tools=[ANSWER_TOOL_ANTHROPIC],
        tool_choice={"type": "tool", "name": "answer_question"},
    )

    # Difference 4: tool-use is a content block, not message.tool_calls.
    tool_block = next(
        (block for block in resp.content if block.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise RuntimeError("Claude did not call the answer_question tool")

    args = tool_block.input  # already a dict in the Anthropic SDK — no json.loads

    # Cost: Anthropic returns usage too, just on resp.usage with different
    # field names. Skipped here — see cost.py RATES for how you'd extend it.
    return Answer(
        content=args["content"],
        confidence=args["confidence"],
        sources=args.get("sources", []),
        cost_usd=0.0,  # extend cost.py RATES with claude-sonnet rates
        retries=0,
        schema_version="v1",
    )


# What does NOT change:
#   - The Answer Pydantic model (same shape across providers).
#   - The retry pattern (try/await/sleep/backoff).
#   - How you persist into SQLite.
#   - The W3 API contract (/ask, /ask_batched still take the same Question
#     and return the same Answer).
#
# This is the production lesson: the abstraction boundary is the Answer model
# and the function signature, not the SDK.

if __name__ == "__main__":
    raise SystemExit(
        "This file is reference-only. Read it, don't run it in the W4 lab."
    )
