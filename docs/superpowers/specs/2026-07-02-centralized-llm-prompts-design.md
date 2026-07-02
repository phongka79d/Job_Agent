# Centralized LLM Prompts Design

## Goal

Centralize all production LLM and system prompt text in one modular Python
package so prompts are easy to find and maintain without changing runtime
behavior.

## Scope

Create `backend/app/prompts/` with:

- `chat.py` for the chat system instructions, bounded-memory system context,
  and chat prompt builder.
- `job_extraction.py` for job extraction and repair templates and builders.
- `__init__.py` as the package boundary, without duplicating prompt content.

Move prompt ownership from:

- `backend/app/agents/prompts.py`
- `backend/app/agents/chat_prompts.py`
- `backend/app/services/chat_llm_client.py`
- `backend/app/services/chat_memory_service.py`

Tool descriptions, deterministic API responses, progress messages, and
frontend text are not LLM prompts and remain in their current modules.

## Behavior

Prompt wording, formatting, interpolation, grounding rules, and provider calls
remain unchanged. Services import prompt constants or builders from
`app.prompts`; they do not define prompt text locally.

The unused legacy chat prompt constant is removed rather than retained as a
second source of truth.

## Migration

1. Add focused prompt modules and tests.
2. Update production and test imports.
3. Delete the obsolete prompt modules under `app/agents`.
4. Search the backend for remaining production LLM/system prompt literals and
   stale references.

## Verification

- Prompt builder unit tests preserve required content and interpolation.
- Backend compilation catches broken imports.
- Full backend tests protect extraction, repair, memory, and chat behavior.
- A final repository search confirms production LLM/system prompt ownership is
  limited to `backend/app/prompts/`.
