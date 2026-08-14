#!/usr/bin/env python3
"""
The finished coding agent from
"Hướng dẫn tự xây dựng một coding agent tối giản" / "How to Build Your Own Coding Agent"
on camnangai.com — every step of the guide, assembled into one runnable file.

    export ANTHROPIC_API_KEY=sk-ant-...
    python agent_script.py --cwd ./target_repo

That drops you at a prompt. Give it the guide's Bước 5 task:

    Viết thêm một endpoint GET /health vào main.py và chạy test cho đến khi pass

`--lang en` switches the console strings to English (the guide's two editions
print different text); `--task "..."` runs one task and exits instead of
prompting. See README.md for how this file maps onto the guide's steps.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import anthropic

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
MODEL = DEFAULT_MODEL
MAX_STEPS = 12

WORKSPACE = Path.cwd().resolve()

STRINGS = {
    "vi": {
        "banner": "Coding agent tối giản — gõ nhiệm vụ, Ctrl-C để thoát",
        "you": "Bạn",
        "tool": "→ Thực thi công cụ",
        "approve": "\n[PHÊ DUYỆT] Agent muốn chạy: {cmd}. Đồng ý? (y/n): ",
        "denied": "User denied execution.",
        "blocked": "Error: Lệnh bị cấm vì lý do bảo mật (chặn rò rỉ dữ liệu hoặc xóa file).",
        "unique": "Error: old_str không xuất hiện duy nhất một lần. Hãy cung cấp ngữ cảnh cụ thể hơn.",
        "done": "✓ Hoàn tất",
        "steps": "Đã đạt giới hạn {n} lượt.",
    },
    "en": {
        "banner": "Minimal coding agent — type a task, Ctrl-C to quit",
        "you": "You",
        "tool": "→ Executing tool",
        "approve": "\nExecute command? [y/N]: {cmd} ",
        "denied": "User denied execution.",
        "blocked": "Error: Command blocked for security reasons (prevents exfiltration or deletion).",
        "unique": "Error: old_string was not found exactly once. Provide more surrounding context.",
        "done": "✓ Done",
        "steps": "Hit the {n}-step limit.",
    },
}

S = STRINGS["vi"]

SYSTEM_PROMPT_TEMPLATE = """You are a coding agent working inside the user's repository.

Your shell already starts in the project root: {cwd}
Every path you use is relative to that directory. Never `cd` anywhere — not to an
absolute path, not to a directory you remember from elsewhere. `main.py` and
`test_main.py` are right here.

Read CLAUDE.md first if it exists — it holds the project's conventions.
Use your tools to inspect and modify files. After every edit, run the test suite
with `pytest -v` and keep iterating until the tests pass. Do not guess at file
contents; read them.
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE

BLOCKED_COMMANDS = ["rm -rf /", "rm -rf *", "env", "curl", "wget"]


# --- tools -------------------------------------------------------------------


def resolve_workspace_path(path_str):
    resolved = (WORKSPACE / path_str).resolve()
    if WORKSPACE not in resolved.parents and resolved != WORKSPACE:
        raise ValueError(f"Path escapes workspace: {path_str}")
    return resolved


def list_files(path="."):
    safe_path = resolve_workspace_path(path)
    return "\n".join(
        str(p.relative_to(WORKSPACE))
        for p in sorted(safe_path.rglob("*"))
        if p.is_file() and "__pycache__" not in str(p)
    )


def read_file(path, offset=0, limit=500):
    safe_path = resolve_workspace_path(path)
    lines = safe_path.read_text().splitlines()
    subset = lines[offset : offset + limit]
    return "\n".join(f"{i + offset + 1} | {line}" for i, line in enumerate(subset))


def edit_file(path, old_str, new_str):
    safe_path = resolve_workspace_path(path)
    content = safe_path.read_text()
    if content.count(old_str) != 1:
        return S["unique"]
    safe_path.write_text(content.replace(old_str, new_str))
    return "Success"


def run_bash(command):
    if any(blocked in command for blocked in BLOCKED_COMMANDS):
        return S["blocked"]

    confirm = input(S["approve"].format(cmd=command))
    if confirm.lower() != "y":
        return S["denied"]

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (60s)."

    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def execute_tool(tool_name, tool_input):
    if tool_name == "list_files":
        return list_files(tool_input.get("path", "."))
    if tool_name == "read_file":
        return read_file(tool_input["path"])
    if tool_name == "edit_file":
        return edit_file(tool_input["path"], tool_input["old_str"], tool_input["new_str"])
    if tool_name == "run_bash":
        return run_bash(tool_input["command"])
    return "Error: Unknown tool"


TOOLS = [
    {
        "name": "list_files",
        "description": "Liệt kê file trong thư mục để định hướng / List files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative directory path"}},
        },
    },
    {
        "name": "read_file",
        "description": "Đọc nội dung file kèm số dòng để phục vụ việc chỉnh sửa.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Đường dẫn file tương đối"}},
            "required": ["path"],
        },
    },
    {
        "name": "edit_file",
        "description": "Chỉnh sửa file bằng cách thay thế một chuỗi xuất hiện duy nhất một lần.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"},
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
    {
        "name": "run_bash",
        "description": "Chạy lệnh shell (test, build). Cần người dùng phê duyệt.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]


# --- the loop ----------------------------------------------------------------


class Agent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = MODEL
        self.history = []

    def run_inference(self, system_prompt, tools):
        return self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=self.history,
            thinking={"type": "adaptive"},
        )

    def turn(self, user_text):
        self.history.append({"role": "user", "content": user_text})

        for step in range(MAX_STEPS):
            response = self.run_inference(SYSTEM_PROMPT, TOOLS)
            self.history.append({"role": "assistant", "content": response.content})

            for block in response.content:
                if block.type == "text" and block.text.strip():
                    print(f"\n{block.text.strip()}\n")

            if response.stop_reason != "tool_use":
                print(S["done"])
                return

            results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"{S['tool']}: {block.name} {block.input}")
                    output = execute_tool(block.name, block.input)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(output),
                        }
                    )

            self.history.append({"role": "user", "content": results})

        print(S["steps"].format(n=MAX_STEPS))


def main():
    global WORKSPACE, S, SYSTEM_PROMPT

    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--lang", default="vi", choices=["vi", "en"])
    parser.add_argument("--task", default=None, help="Run one task non-interactively")
    args = parser.parse_args()

    S = STRINGS[args.lang]
    os.chdir(args.cwd)
    WORKSPACE = Path.cwd().resolve()
    SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.format(cwd=WORKSPACE)

    # Either credential works: x-api-key for Anthropic direct, bearer for a proxy.
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_AUTH_TOKEN"):
        sys.exit("Set ANTHROPIC_API_KEY, or run: source ./use-vilao.sh <key>")

    print(f"{S['banner']}  [{WORKSPACE}]")
    agent = Agent()

    if args.task:
        agent.turn(args.task)
        return

    while True:
        try:
            user_text = input(f"\n{S['you']}> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if user_text.strip():
            agent.turn(user_text)


if __name__ == "__main__":
    main()
