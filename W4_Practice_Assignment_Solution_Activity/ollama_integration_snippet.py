"""ollama_integration_snippet.py — W4 activity reference (corrected).

Integrate Ollama into the existing W4 pipeline.

WHAT CHANGED FROM THE FIRST DRAFT
---------------------------------
1. Backend routing is now explicit, driven by one shared list of local
   models, instead of guessing from the model-name prefix.
2. Removed `tool_choice` on the Ollama path. Ollama's OpenAI-compatible
   endpoint does not support `tool_choice` — it accepts `tools` but
   ignores any attempt to force a specific call. The OpenAI path uses
   the correct nested shape.
3. The fallback no longer swallows errors. `except Exception: pass`
   meant every failure looked identical, and students would conclude
   "small models can't tool-call" when the real cause was a rejected
   request. Now the reason is logged.
4. JSON mode upgraded to Structured Outputs (json_schema + strict).

Apply inline to src/pipeline/cost.py and src/pipeline/pipeline.py.
"""

import json
import logging

from openai import AsyncOpenAI

log = logging.getLogger(__name__)


# ─── In src/pipeline/cost.py ────────────────────────────────────────────

# One source of truth for which models run locally. Both the cost table
# and the client factory read from this, so they can't drift apart.
LOCAL_MODELS = frozenset({
    "llama3.2:3b",
    "llama3.1:8b",
    "qwen2.5:7b",
    "mistral:7b",
})

# Add to your existing RATES dict. Local inference is free, so both the
# input and output rate are zero — but the entry must exist or the cost
# calculation raises KeyError.
RATES_ADDITION = {model: (0.0, 0.0) for model in LOCAL_MODELS}


# ─── In src/pipeline/pipeline.py — near the top of the file ─────────────

OLLAMA_BASE_URL = "http://localhost:11434/v1"


def _is_local(model: str) -> bool:
    """True if this model should be routed to Ollama."""
    return model.removeprefix("ollama:") in LOCAL_MODELS


def _model_name(model: str) -> str:
    """Strip our routing prefix — Ollama doesn't know about `ollama:`."""
    return model.removeprefix("ollama:")


def _make_client(settings) -> AsyncOpenAI:
    """Return an AsyncOpenAI client pointed at the right backend.

    Ollama exposes an OpenAI-compatible endpoint, so the same SDK works
    against both — only the base_url changes.

    Routing prefers an explicit `settings.backend` if you have one;
    otherwise it falls back to the LOCAL_MODELS list. Either way the
    decision is data, not a string-prefix guess.
    """
    backend = getattr(settings, "backend", None)
    if backend == "ollama" or (backend is None and _is_local(settings.model)):
        return AsyncOpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",  # required by the SDK, ignored by Ollama
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)


# Then in ask_llm and stream_answer, replace:
#     client = AsyncOpenAI(api_key=settings.openai_api_key)
# With:
#     client = _make_client(settings)


# ─── Structured Outputs schema ──────────────────────────────────────────

# This schema satisfies OpenAI's strict-mode rules, which are tighter
# than what Ollama requires:
#   - every property listed in "required" (no optional fields)
#   - "additionalProperties": false on every object
# A schema that works locally can still be rejected by OpenAI if you
# skip either of these.
#
# Note: strict mode enforces STRUCTURE, not VALUES. `minimum`/`maximum`
# are not applied, so clamp confidence in your own code.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "The answer to the question.",
        },
        "confidence": {
            "type": "number",
            "description": "How confident the model is, from 0.0 to 1.0.",
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Identifiers of the retrieved chunks used.",
        },
    },
    "required": ["content", "confidence", "sources"],
    "additionalProperties": False,
}

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "answer_question",
        "schema": ANSWER_SCHEMA,
        "strict": True,
    },
}


# ─── Tool-calling with a structured-output fallback ─────────────────────

async def ask_llm_with_fallback(question, settings):
    """Try tool-calling; fall back to Structured Outputs.

    Small local models comply with tool-calling inconsistently, so we
    keep a fallback. But note WHY each path is shaped the way it is:

    - OpenAI supports `tool_choice`, so we can force the call.
    - Ollama does NOT support `tool_choice`. We pass `tools` and let
      the model decide, then check whether it actually called.

    Structured Outputs is the more reliable path on both backends,
    because the decoder is constrained to the schema rather than being
    asked nicely. Tool calling earns its place when the model must
    choose between several actions; here we only want a shaped answer.
    """
    client = _make_client(settings)
    model = _model_name(settings.model)
    local = _is_local(settings.model)

    request = {
        "model": model,
        "messages": [{"role": "user", "content": question.question}],
        "tools": [ANSWER_QUESTION_TOOL],  # your existing tool spec
    }
    if not local:
        # Correct Chat Completions shape — the name nests under
        # "function". Omitted for Ollama, which ignores this field.
        request["tool_choice"] = {
            "type": "function",
            "function": {"name": "answer_question"},
        }

    try:
        response = await client.chat.completions.create(**request)
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            return _parse_tool_call(tool_calls[0], response.usage, model)
        log.info("Model %s returned no tool call; using structured output.", model)
    except Exception as exc:
        # Log it. A silent `pass` here hides malformed requests, auth
        # failures, and a stopped Ollama daemon behind one symptom.
        log.warning("Tool-calling failed for %s: %s", model, exc)

    # Fallback: Structured Outputs.
    #
    # Requires Ollama >= 0.5.0 for the json_schema form. Older builds
    # ignore it silently and return unconstrained text, so pin a
    # version in the activity setup. If you must support older Ollama,
    # use {"type": "json_object"} plus a schema description in the
    # system prompt.
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Answer the question using the provided schema.",
            },
            {"role": "user", "content": question.question},
        ],
        response_format=RESPONSE_FORMAT,
    )

    message = response.choices[0].message

    # Structured Outputs adds a failure mode JSON mode doesn't have:
    # the model can refuse instead of returning JSON.
    if getattr(message, "refusal", None):
        raise ValueError(f"Model refused: {message.refusal}")

    parsed = json.loads(message.content)
    parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
    return _parse_json_response(parsed, response.usage, model)


# ─── Verifying the fix ──────────────────────────────────────────────────
#
# Before this correction, the tool-calling path failed silently every
# run. To confirm it's now visible, enable logging and watch which
# branch you land in:
#
#     logging.basicConfig(level=logging.INFO)
#
# A local run should log either "returned no tool call" (the model
# genuinely didn't comply — the real lesson) or a specific error (a
# request problem — fix it). Seeing neither means tool calling worked.
#
# Helpers _parse_tool_call, _parse_json_response, ANSWER_QUESTION_TOOL
# are already defined in your W4 pipeline.py. Note that
# _parse_json_response now takes a parsed dict rather than the raw
# response — adjust its signature to match.