# max (maximum time efficiency)

A personal scheduling system that automatically optimizes daily task allocation based on deadlines and priorities, with natural language control via OpenClaw.

## Project Structure

- **kernel/** — Core scheduling: `kernel.py` (implementation) and `syscalls.py` (syscall layer). External code uses `kernel.syscalls` only.
- **mcp_servers/** — MCP server exposing tools that call the kernel API; includes composite workflow tools (e.g. create and show today).
- **mcp_client/** — OpenClaw integration and Discord interface
- **docs/KERNEL_AND_SYSCALL_SPEC.md** — Spec for every kernel class/attribute/method and every API syscall (including direct vs composite mapping)



The Problem:

You wake up with 5 courses, assignments with different deadlines, gym sessions, meals, portfolio work—all competing for limited hours (6am-midnight). Every day you're mentally juggling: "What's urgent? What can wait? Did I forget something?" It's exhausting cognitive overhead that drains energy before you even start working.
Your Solution:
A personal scheduling agent that thinks for you. You dump all your responsibilities into it once (or as they come up), and it continuously figures out the optimal day-by-day plan. No manual calendar Tetris. No forgetting deadlines. No decision fatigue about "what should I work on next?"

## Architecture

1. **kernel/** — `kernel.py` = implementation; **kernel/syscalls.py** = syscall layer (the only code that uses kernel types). All callers use `kernel.syscalls` only.
2. **mcp_servers/** — MCP tools call `kernel.syscalls`. Granular tools = one syscall each; composite tools (e.g. create_process_and_show_today) = multiple syscalls for common LLM requests.
3. **mcp_client/** — User interface via Discord/OpenClaw.

## Status

In active development.
