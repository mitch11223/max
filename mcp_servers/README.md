# MCP Servers

MCP server that exposes Max scheduling to LLM clients (Cursor, OpenClaw, etc.). Tools call **kernel.syscalls**, not the kernel implementation.

## Architecture

- **MCP server** (`max_server.py`) — Lists tools; each tool invokes one or more syscalls, returns JSON.
- **Kernel syscalls** (`../kernel/syscalls.py`) — Syscall layer; owns ProcessTable, Schedule, Dispatcher; only layer that imports kernel implementation.
- **Kernel** (`../kernel/kernel.py`) — Internal; not imported by the server.

So: **LLM → MCP tools → kernel.syscalls → kernel.kernel.**

**Orchestration:** A request like “create a process and show my day” can be satisfied by:
1. **LLM** calling several tools in sequence (e.g. max_create_process, max_build_schedule, max_get_schedule_view), or  
2. **One composite tool** (e.g. max_create_process_and_show_today) that runs several syscalls and returns combined result.  
The server provides both granular and composite tools; see `docs/KERNEL_AND_SYSCALL_SPEC.md`.

## Running the server

From the **project root** (`max/`):

```bash
# Install MCP SDK once
pip install mcp anyio

# Run over stdio (for Cursor / Claude Desktop)
python mcp_servers/max_server.py
```

Or as a module:

```bash
cd /path/to/max
python -m mcp_servers.max_server
```

The server adds the project root to `sys.path` so `import kernel.syscalls` works.

## Tools

See `docs/KERNEL_AND_SYSCALL_SPEC.md` for the full list. Examples:

- `max_create_process` — create a task (name, deadline, duration, priority, …)
- `max_list_processes`, `max_get_process`, `max_remove_process`
- `max_load_processes`, `max_save_processes`
- `max_initialize_schedule`, `max_build_schedule`
- `max_get_schedule_view`, `max_get_schedule_range`
- `max_assign_slot`, `max_clear_slot`, `max_clear_all_assignments`
- `max_get_stats`, `max_get_next_deadline`, `max_set_urgency_function`
- `max_admit_all_processes`

## Dependencies

- Python 3.10+
- `mcp` (MCP Python SDK)
- `anyio` (for stdio server)
- Project `kernel/` (contains `syscalls.py`) and project root on path.
