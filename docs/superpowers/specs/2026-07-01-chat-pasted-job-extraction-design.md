# Chat Pasted Job Extraction Design

## Summary

Add a chat-first flow where the user can paste a job description directly into the Agent Chat. The agent detects likely job-post text, runs a visible `extract_job_from_text` tool, persists the extracted job through the existing ingestion/scoring pipeline, and points the user to Review Queue.

This is not a new ingestion architecture. It reuses the existing production path:

- `extract_from_raw_text(...)`
- LangGraph extraction workflow
- `process_job_state(...)`
- SQLite persistence
- scoring
- Qdrant sync when the job is scorable
- Review Queue status

All runtime/user-facing copy is English.

## User Behavior

When a user pastes a job post or job description into chat, the agent should:

1. Detect that the message is likely pasted job text.
2. Create and display an `extract_job_from_text` tool call.
3. Stream visible progress events while extraction/scoring runs.
4. Persist the extracted job if extraction succeeds.
5. Return a concise English summary.
6. Navigate or guide the user to Review Queue when at least one job is inserted.

Example assistant response:

```text
Called 1 tool: Extract job from text.
Added 1 job to Review Queue. Open Review Queue to inspect and approve it.
```

If extraction fails, the assistant should report the failure and keep the chat stable:

```text
Called 1 tool: Extract job from text, but extraction failed. Check that the pasted text contains a real job description and try again.
```

## Detection Rules

The agent should use a conservative deterministic heuristic before running extraction. It should classify a message as likely pasted job text when the message:

- is longer than a normal short chat prompt, and
- contains multiple job-post signals such as responsibilities, requirements, qualifications, skills, company, location, salary, benefits, apply, job description, or about the role.

If the heuristic is uncertain, the agent should not ingest data silently. It should ask for confirmation in normal chat instead.

Existing Vietnamese intent keywords may remain as hidden compatibility signals, but new runtime UI and assistant messages must be English.

## Tool Design

Add a real `extract_job_from_text` handler to the existing tool registry.

Tool input:

- `raw_text`
- `role_profile_id`
- optional `source_url`
- optional progress callback

Tool output:

- `content`
- `result_summary`
- `safe_payload`

Safe payload should include only frontend-safe fields:

- `inserted_jobs`
- `skipped_duplicates`
- `warning_count`
- `review_queue_path`
- optional inserted `job_ids`
- optional `batch_id`

It must not expose raw LLM provider payloads, API keys, prompts, hidden metadata, or full pasted text back to the frontend.

## Visible Tool Calls

The frontend should show the tool in the existing tool-call timeline with these states:

- `pending`
- `running`
- `success`
- `failed`

Suggested visible progress messages:

- `Preparing pasted job text...`
- `Extracting structured job data...`
- `Scoring against the active profile...`
- `Saving job to Review Queue...`

The tool call summaries should be concise:

- input summary: `Pasted job text, <N> characters`
- success summary: `Added 1 job to Review Queue.`
- failure summary: `Job text extraction failed.`

## Backend Flow

`routes_chat.py` should choose agent path in this order:

1. search intent -> existing `search_jobs`
2. likely pasted job text -> new `extract_job_from_text`
3. otherwise -> normal chat LLM response

The route should stay thin. Tool business logic belongs in service/tool-registry code, not directly in route handlers.

The new tool handler should reuse existing extraction and processing services rather than duplicating parse/scoring logic from `/api/jobs/parse-text`.

## Frontend Flow

The chat UI should not add a separate form for this behavior. The main chat composer is the entry point.

While the agent is working, the chat transcript should show:

- assistant/server progress status
- visible tool call card
- progress logs
- final assistant message

On successful insertion, the existing review navigation behavior can be reused:

- refresh batch metrics when possible
- open Review Queue when `review_queue_path` is `/review` and `inserted_jobs > 0`

## Safety Rules

- Do not invent job data.
- Do not create a job unless the message is likely a job post or the user explicitly asks to parse/analyze the pasted text.
- Do not expose hidden tool payloads, provider responses, API keys, prompts, or full raw pasted text through `safe_payload`.
- Do not delete or overwrite existing jobs.
- Preserve duplicate handling through existing ingestion logic.
- Keep test doubles test-only.

## Tests

Backend tests should cover:

- chat stream detects pasted job text and calls `extract_job_from_text`
- visible tool call is persisted with sanitized summaries
- successful extraction inserts a job and emits `tool_call_completed`
- failed extraction emits `tool_call_failed` and persists a safe assistant message
- non-job chat messages still use normal chat LLM behavior

Frontend tests should cover:

- pasted job chat stream displays tool progress events
- successful `extract_job_from_text` payload navigates to Review Queue
- failures show a visible error/tool failure without leaking raw payload

## Non-Goals

- No OCR.
- No new job ingestion architecture.
- No new demo/mock runtime data.
- No silent data deletion or overwrite behavior.
- No broad UI redesign beyond visible tool-call handling needed for this flow.
