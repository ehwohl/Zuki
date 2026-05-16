# Zuki — CLAUDE.md

> Role: Senior Software Architect. Code first, explanations after. No small talk.
> On conflict: REFERENCES.md wins over this file. This file is the map, REFERENCES.md is the truth.

\---

## Language Rule

|Layer|Language|Rule|
|-|-|-|
|Code, docs, comments, architecture|**English**|Always. No exceptions.|
|Terminal output, logs, Zuki speech|**German**|Via `ui.\*` methods only — never raw `print()`|

\---

## Workspace Routing

|Workspace|Location|Primary Docs|Key Rule|
|-|-|-|-|
|**Core**|`core/`|`REFERENCES.md §1,5,6,7,8,10,11`|`LLMManager` in `main.py` only; all skills use `APIManager`; no `print()` below `ui.py`|
|**Broker Suite**|`workspaces/broker/`|`REFERENCES.md §2,14,16`|Receives n8n webhooks via `webhook\_receiver.py`; no active scraping in Zuki core|
|**Business Services**|`workspaces/business/`|`REFERENCES.md §13,16,17`|Inline interview pattern; PDF reports → `temp/business\_reports/`; DSGVO-aware|
|**OS Layer**|`core/text\_to\_speech/` `tools/window\_control/` `workspaces/os/`|`REFERENCES.md §15`|ABC backends, factory via `sys.platform`; Linux stubs: Piper TTS + xdotool; every backend: `get\_status() → dict`|
|**Cloud Memory**|`tools/cloud\_memory.py` `zuki\_cloud/`|`REFERENCES.md §2,3,9,13`|`cloud.save()` never gated by simulation; `REDIS\_URL` only; schema `"v": 1`; tenant isolation mandatory|
|**UI Shell**|`ui/` `ui\_bridge.py`|`PRODUCT.md` `DESIGN.md`|React PWA; Zustand only; no Redux/Context; CSS vars for all tokens; glow-pulse via direct DOM write|

\---

## External Infrastructure

|Service|Role|Status|Boundary|
|-|-|-|-|
|**n8n** (local install)|Data ingestion — polls APIs, filters RSS, fires webhooks into Zuki|**Planned, not active**|Entry point: `workspaces/broker/webhook\_receiver.py` only|
|**Vercel KV / Redis**|Cloud memory, tenant data|Active|`zuki\_cloud/` via `REDIS\_URL`|
|**Vercel Serverless**|Cloud API endpoints|Active|`zuki\_cloud/api/`|

**n8n contract:** n8n collects and filters — Zuki decides and acts. Nothing from n8n ever reaches `core/` directly. When n8n becomes active, `workspaces/broker/scraper.py` and `core/news\_manager.py` are deleted.

\---

## Skill Routing (Two-Stage)

```
Command input  ──OR──  n8n webhook (future, → webhook\_receiver.py)
        │
        ▼
\[Stage 1] skill\_registry.get\_skill\_for(cmd)   ← exact trigger match, 0 tokens
        │ no match
        ▼
\[Stage 2] RouterAgent.route()                  ← LLM call, \~80 token output
        │ SIM mode → returns \[] immediately
        ▼
Skill.handle()
```

* Skills without `description` are invisible to the router — always set it.
* New skills: single-task file inside the correct Workspace folder.
* `tenant\_aware = True` is the default for all new skills.

\---

## Hard Rules (non-negotiable)

1. `cloud.save()` is never wrapped in `if not simulation:` — cloud integrity is independent of LLM state.
2. No `print()` outside `core/main.py` and `core/ui.py` — use `logging.\*` everywhere else.
3. New LLM calls outside `main.py` use `APIManager`, not `LLMManager`.
4. All user-facing errors: `\_write\_error\_log()` → `logs/error.log`, then `\_friendly\_error()` → German sentence.
5. Stubs raise `NotImplementedError` — never caught in generic `except Exception`.
6. `.env` is never committed — `system test github` actively verifies this.
7. Linux-targeting code goes into existing stubs only — never into `core/` directly.
8. n8n communicates via HTTP webhook only — never imported into Python core.

\---

## What Lives Where

|Thing|Correct Location|Dead / Wrong|
|-|-|-|
|New Skill / Task|`workspaces/<name>/`|`core/`|
|TTS implementation|`core/text\_to\_speech/<platform>\_tts.py`|anywhere else|
|Window control|`tools/window\_control/<platform>\_backend.py`|`core/`|
|Data ingestion / polling|**n8n** (when active)|`core/news\_manager.py` ← dead|
|Web scraping|**n8n** (when active)|`workspaces/broker/scraper.py` ← dead|
|n8n entry point|`workspaces/broker/webhook\_receiver.py`|`core/`|
|Industry knowledge|`knowledge/<industry>.yaml`|hardcoded in skill|
|Business reports|`temp/business\_reports/` (gitignored)|`logs/`|
|User profile|`memory/user\_profile\_{tenant}.txt`|anywhere in `core/`|
|Secrets|`.env` only|code, docs, anywhere|



