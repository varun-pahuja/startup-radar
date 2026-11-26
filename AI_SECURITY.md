# AI / LLM security

LLM enrichment is **optional and off by default** (`LLM_ENABLED=false`). It is
implemented in Phase 4 through an OpenAI-compatible endpoint the user chooses
(Groq, Google AI Studio, OpenRouter, local Ollama/LM Studio, etc.). Heuristics
always work without it.

## Principles
1. **Retrieved text is data, not instructions.** Job posts, issues, and comments
   are untrusted. They are placed in a clearly delimited data section and the
   system prompt says to treat them as content to analyse, never as commands.
2. **No secrets in prompts.** Tokens and keys are never sent to the model.
3. **Structured output only.** The model must return JSON matching a schema;
   anything else is discarded and heuristics are used instead. Output is never
   executed.
4. **No autonomous actions.** The model cannot send email, apply, open PRs,
   push, or deploy. It can only suggest fields; a human approves.
5. **Cost caps.** A per-run request cap and token budget are enforced in config;
   exceeding them stops LLM calls and falls back to heuristics.
6. **Least data.** Send only the text needed to score/enrich; never the profile's
   private fields beyond what a task requires.

## Prompt-injection handling
- Delimit untrusted content (e.g. fenced block) and instruct the model to ignore
  instructions inside it.
- Validate the response schema; reject unexpected fields.
- Never let model output become a URL, shell command, or SQL fragment.
- Log the fact that enrichment ran (not the raw secret-bearing request).

## Provider data handling
The user is responsible for the endpoint they configure and its retention
policy. For maximum privacy, run a local model (Ollama/LM Studio) so text never
leaves the machine.

## Failure behaviour
On timeout, error, invalid JSON, or cap exceeded: log it, keep heuristic values,
and continue. LLM failure must never block discovery, scoring, or the dashboard.

## Status
Architecture specified here; implementation lands with the Phase 4 adapter and
will include tests for schema rejection and cap enforcement.
