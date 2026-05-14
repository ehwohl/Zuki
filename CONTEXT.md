# Zuki — CONTEXT.md

## Current Project
Restructuring Zuki from monolithic workspaces folder into a 5-Workspace architecture.
Parallel goal: prepare Linux migration (Pop!_OS / Ubuntu 24.04).
Bundle 12 done. No active bundle. Next: Bundle 10 (Office) or Bundle 13 (UI).

## What Good Looks Like
- New skills are single task files inside their Workspace folder
- Every new Manager has `get_status() → dict`
- `cloud.save()` never gated by `llm.simulation`
- All LLM calls in new skills use `APIManager`, not `LLMManager`
- Linux-targeting code goes into existing stubs only

## What to Avoid
- `print()` outside `core/main.py` and `core/ui.py`
- New `LLMManager` calls outside `main.py` — documented debt, don't spread it
- State machines in `main.py` for skill interviews — use inline `ui.user_prompt()`
- Platform-specific code in `core/` — OS Layer workspace only
