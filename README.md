# janus-skills-library

Skill library for [Positronic Membrane](https://github.com/jmccauley75gh/positronic-membrane). Skills are Python source files stored here and loaded into Positronic Membrane's `agent_skills` database table at boot via `sync_from_registry()`.

---

## How skills work

Each skill is a Python source file with a single entry-point function (typically `run`). At runtime, `DynamicSkillExecutor` in Positronic Membrane compiles the source and executes it in a namespace pre-populated with an `sdk` dict of Safe\* wrapper instances. Skills access system capabilities exclusively through this dict.

Skills are registered in `registry.json` at the repo root. On every Positronic Membrane boot (and on demand via the `sync_skill_library` skill), the harness clones or pulls this repo, runs each skill's test file, and — if tests pass — writes the skill into the `agent_skills` table.

---

## Version lines

This repo has two long-lived branches, mirroring the main repo's successor model
(`docs/successor_spec.md` there):

| Branch | Purpose | `sdk_version` |
|---|---|---|
| `v1` | Frozen to match the `Safe*` SDK wrapper surface of the current, in-production main repo. No new `sdk` capabilities, only bug fixes and new skills built against the existing surface. | `"v1"` |
| `v2` | Where skill development for the successor instance happens, once its `Safe*` SDK surface diverges from `v1`. | `"v2"` |

Each branch's `registry.json` declares its line in a top-level `"sdk_version"` field.
Positronic Membrane instances pin to a branch via the `skills.library_ref` `system_config`
key (default `"v1"`, human-locked) and reject any synced skill whose declared
`sdk_version` doesn't match their own `SDK_MAJOR_VERSION` constant — at boot-sync time,
not execution time. A registry with no `sdk_version` field is treated as compatible with
any instance (legacy/back-compat default), so the field is optional defense-in-depth on
top of branch isolation, not the only thing enforcing the pin.

**Freeze rules for `v1`:** once a main-repo instance is running against `v1` in
production, do not add skills to `v1` that call `sdk` capabilities it doesn't yet expose,
and do not change the meaning/shape of an existing skill's parameters or return value.
New skills that only use the existing `sdk` surface, and pure bug fixes, are fine.
Anything that needs a new or changed `Safe*` capability belongs on `v2` instead.

`main` continues to receive general repo maintenance (docs, tooling, CI) and is not
itself synced by any running instance — `v1`/`v2` are cut from it and are the only
branches instances actually pin to.

---

## Adding a new skill

### 1. Create the skill file

Add `skills/<skill_id>.py`. The file must define the entry-point function named in `registry.json` (usually `run`):

```python
def run(action, **kwargs):
    # sdk is injected at runtime — access system capabilities through it
    result = sdk["db"].query("SELECT count(*) FROM goals")
    return {"count": result[0][0]}
```

The `sdk` dict is available as a module-level name — do not import it, it is injected before execution.

### 2. Create the test file

Add `skills/test_<skill_id>.py`. Tests must load the skill via `importlib` and inject a mock `sdk` — they cannot import the skill directly because `sdk` is not defined at import time:

```python
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

def _load_skill():
    spec = importlib.util.spec_from_file_location(
        "my_skill", Path(__file__).parent / "my_skill.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.sdk = {"db": MagicMock(), "logger": MagicMock()}
    spec.loader.exec_module(mod)
    return mod

def test_entry_point_defined():
    mod = _load_skill()
    assert callable(mod.run)
```

### 3. Register in registry.json

Add an entry to the `"skills"` array:

```json
{
  "skill_id": "my_skill",
  "name": "My Skill",
  "description": "One sentence description of what this skill does.",
  "parameters_schema": "{\"type\":\"object\",\"properties\":{\"action\":{\"type\":\"string\"}},\"required\":[\"action\"]}",
  "entry_point_function": "run",
  "required_role": "user",
  "trigger_type": "manual",
  "trigger_config": "{}",
  "file": "skills/my_skill.py",
  "test_file": "skills/test_my_skill.py"
}
```

---

## registry.json schema

| Field | Type | Description |
|---|---|---|
| `skill_id` | string | Unique identifier (snake_case). Primary key in `agent_skills`. |
| `name` | string | Human-readable name shown in the UI. |
| `description` | string | One-sentence description of what the skill does. |
| `parameters_schema` | string (JSON) | JSON Schema for the arguments the entry-point function accepts. |
| `entry_point_function` | string | Name of the Python function to call in the skill file. |
| `required_role` | string | Minimum role to invoke: `observer`, `user`, `contributor`, or `admin`. |
| `trigger_type` | string | `manual` (invoked explicitly) or `interval` (daemon-scheduled). |
| `trigger_config` | string (JSON) | For `interval` triggers: `{"interval_seconds": 30}`. Empty `{}` for manual. |
| `file` | string | Path to the skill source file relative to the repo root. |
| `test_file` | string | Path to the test file relative to the repo root. |

Top-level, alongside `"skills"`: an optional `"sdk_version"` field (e.g. `"v1"`) declares
which SDK line this branch's registry targets — see [Version lines](#version-lines).
Individual skill entries may also carry their own `"sdk_version"` override for the rare
case where a single skill needs to be pinned differently than the rest of the registry.

---

## SDK reference

The `sdk` dict injected into every skill namespace:

| Key | Type | What it provides |
|---|---|---|
| `db` | `SafeDB` | SQL queries against the Janus database (safety-checked; cannot touch `core_constitution`) |
| `fs` | `SafeFS` | Filesystem reads/writes bounded to the active workspace root |
| `memory` | `SafeMemory` | Semantic memory: `add_memory()`, `query_memories()` |
| `swarm` | `SafeSwarm` | Inter-agent messaging and `validate_action()` |
| `goals` | `SafeGoals` | Goal CRUD and checkpoint management |
| `documents` | `SafeDocuments` | Persistent document store |
| `sandbox` | `SafeSandbox` | Ad-hoc Python code execution in the AST-audited sandbox |
| `self_model` | `SafeSelfModel` | Read/write self-model traits |
| `drives` | `SafeDrives` | Boredom and curiosity drive state |
| `orchestration` | `SafeAgentOrchestration` | Dispatch tasks and manage sandbox sessions |
| `replication` | `SafeReplication` | Spawn child Janus instances |
| `cognition` | `SafeLayeredCognition` | Access daemon cognitive layer state |
| `explorer` | `SafeExplorer` | Web search and page fetch |
| `codebase` | `SafeCodebase` | Codebase index query |
| `github` | `SafeGitHub` | GitHub REST API: issues, PRs, comments |
| `logger` | `logging.Logger` | Standard Python logger scoped to the skill |

Skills can also use the Python standard library and any package installed in Positronic Membrane's virtualenv directly — `__builtins__` is fully available.

---

## Existing skills

| Skill | Description |
|---|---|
| `checkout_db_to_draft` | Retrieve a document from the database and save it to a local draft file |
| `cleanup_episodic_memory` | Apply TTL cleanup to older episodic memory rows |
| `cleanup_llm_cache` | Apply TTL cleanup to older LLM cache rows |
| `commit_draft_to_db` | Read a draft file and publish it into the document store |
| `consolidate_memories` | Trigger memory consolidation to synthesise granular logs into long-term memory |
| `decay_self_model` | Apply background time decay to unpinned self-model traits |
| `delete_db_document` | Delete a persistent document from the document store |
| `delete_draft_file` | Delete a draft file from `docs/drafts/` |
| `document_memory` | Retrieve or list persistent documents |
| `echo_message` | Return the provided message as-is (example/template skill) |
| `evaluate_drives` | Increment and evaluate system drives like boredom |
| `evaluate_goals` | Check active goals and transition completed ones |
| `execute_code` | Compile and run Python code in the AST-audited sandbox |
| `fetch_url` | Fetch and parse the text contents of a URL |
| `github_integration` | GitHub REST API: list/read issues, create issues, add comments, open PRs |
| `ingest_fact` | Run a candidate fact through the 4-phase epistemic ingestion pipeline |
| `list_draft_files` | List all draft files in `docs/drafts/` |
| `manage_sandbox` | Control git worktree sandboxes (start, test, ship, abort, diff) |
| `neo4j_keepalive` | Daily read-only ping of the Neo4j graph to prevent Aura Free auto-pause |
| `read_codebase` | Query the codebase index for class structures, methods, and patterns |
| `read_draft_file` | Read a draft document from `docs/drafts/` |
| `run_reflection_cycle` | Execute the autonomous multi-agent reflection and debate loop |
| `scan_workspace` | Recursively scan the workspace, parse Python ASTs, and index the codebase |
| `spawn_agent` | Register or update a helper agent in the swarm registry |
| `web_search` | Perform a web search and retrieve a list of results |
| `write_draft_file` | Write or update a draft document in `docs/drafts/` |

---

## How the boot sync works

On every Positronic Membrane boot (`init_db()` in `src/database.py`):

1. The `sync_skill_library` skill (hardcoded in `init_db`) bootstraps the process.
2. `sync_from_registry()` in `src/skill_harness.py` clones or pulls this repo into `.janus_sandboxes/skills_library/`.
3. For each skill entry in `registry.json`, the harness copies the skill file to a temp location, runs its test file via pytest, and — only if all tests pass — upserts the skill into the `agent_skills` table.
4. Skills that fail their tests are skipped with a warning logged; they do not overwrite a previously working version.

To re-sync without rebooting, run the `sync_skill_library` skill from the Persona chat:
```
/runskill sync_skill_library
```
