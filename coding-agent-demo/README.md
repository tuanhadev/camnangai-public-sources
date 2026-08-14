# coding-agent-demo

A minimal **coding agent** — a ReAct loop around the Anthropic Messages API, with
tools to list, read and edit files, plus shell access behind a human approval
gate. Point it at a repo and it reads the code, edits it, runs the tests, and
keeps going until they pass.

This is the finished project for:

- 🇻🇳 [Hướng dẫn tự xây dựng một coding agent tối giản](https://camnangai.com/ung-dung-ai/lap-trinh-vien/tu-xay-dung-coding-agent)
- 🇬🇧 [How to Build Your Own Coding Agent](https://camnangai.com/en/for/developers/build-your-own-coding-agent)

## Project structure

```text
coding-agent-demo/
├── agent_script.py       # the whole agent: tools, ReAct loop, CLI
├── requirements.txt
├── reset.sh              # put target_repo back to its "before" state
└── target_repo/          # the sample repo you point the agent at
    ├── CLAUDE.md         # project context, from Bước 5 / Step 5
    ├── main.py           # a FastAPI app with no /health endpoint
    └── test_main.py      # ...and a test that demands one (fails at first)
```

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python agent_script.py --cwd ./target_repo
```

Then give it the task from the guide's last step:

```text
Viết thêm một endpoint GET /health vào main.py và chạy test cho đến khi pass
```

It will ask permission before every shell command — answer `y` to let `pytest`
run. When it finishes, `target_repo` has a working `/health` endpoint and both
tests pass. Run `./reset.sh` to try again from scratch.

Useful flags: `--lang en` prints the English console strings (the guide's two
editions print different text), and `--task "..."` runs a single task and exits
instead of prompting.

## Which part of the guide produces what

| Guide step                          | Where it lands in `agent_script.py`                        |
| ----------------------------------- | ---------------------------------------------------------- |
| Bước 1 — the conversation loop      | `Agent.__init__`, `Agent.run_inference`                     |
| Bước 2 — first tool + `tool_use`    | `TOOLS`, `execute_tool`, the dispatch inside `Agent.turn`   |
| Bước 3 — read / write / edit tools  | `resolve_workspace_path`, `list_files`, `read_file`, `edit_file` |
| Bước 4 — shell behind an approval gate | `BLOCKED_COMMANDS`, `run_bash`                           |
| Bước 5 — run it on a real repo      | `main()`, and `target_repo/`                                |

The names match the guide: the workspace guard is `resolve_workspace_path`, the
edit tool is a unique-string replacement, and `run_bash` prompts before it runs.

## What this sample adds beyond the guide

The guide teaches in fragments — it shows the ReAct dispatch as a snippet and
leaves the surrounding loop implied, because a full listing in the middle of a
step would bury the idea being taught. This file closes those gaps:

- **The complete loop.** `Agent.turn` assembles `tool_result` blocks, appends
  them to the history, and iterates until `stop_reason` is no longer `tool_use`.
  It stops at `MAX_STEPS = 12`, which is the `max_steps` guard the guide's
  troubleshooting table recommends.
- **All four tool schemas.** The guide gives `read_file`'s JSON Schema in full
  and describes the rest; here every tool carries its own schema.
- **The system prompt**, referenced as `SYSTEM_PROMPT` in the guide but never
  printed there. It tells the agent to read `CLAUDE.md` and to keep running the
  tests after each edit.
- **A repo to point it at.** Bước 5 describes a FastAPI project; `target_repo/`
  is that project, starting from a deliberately failing `test_health`.
- **Console strings in both languages**, so one file serves both editions.

One deliberate deviation: the guide writes
`anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))`, while this file
calls `anthropic.Anthropic()`. The SDK reads `ANTHROPIC_API_KEY` from the
environment on its own, and the no-argument form also honours `ANTHROPIC_BASE_URL`
if you route through a proxy. Behaviour is identical when the variable is set.

## A word on safety

`run_bash` executes with your user's permissions. The approval prompt is the
only thing between the model and your machine, and `subprocess` is **not** a
sandbox — the guide's Bước 4 makes this point and it is worth repeating here.
Read each command before you approve it. If you want to let it run unattended,
put it in a container without network access first.
