# Max MCP Server — thin tool layer over the Max API.
# Run from project root: python -m mcp_servers.max_server
# Or: cd /path/to/max && python mcp_servers/max_server.py
# Requires: pip install mcp

import json
import sys
from pathlib import Path

# Ensure project root is on path so we can import kernel.syscalls
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import kernel.syscalls as syscalls


def _tool_result_text(data):
    """Format API result as MCP tool result content."""
    if isinstance(data, (dict, list)):
        text = json.dumps(data, indent=2)
    else:
        text = str(data)
    return [{"type": "text", "text": text}]


def _create_and_schedule(name, process_type="one-time", deadline=None, expected_completion_time=60,
                         base_priority=3, tags=None, location=None):
    """Composite: create_process + admit_all_processes + build_schedule."""
    from datetime import datetime
    create_result = syscalls.create_process(
        name=name, process_type=process_type, deadline=deadline,
        expected_completion_time=expected_completion_time, base_priority=base_priority,
        tags=tags or [], location=location,
    )
    if not create_result.get("ok"):
        return create_result
    syscalls.admit_all_processes()
    build_result = syscalls.build_schedule()
    return {"ok": True, "create": create_result, "build": build_result}


def _create_and_show_today(name, process_type="one-time", deadline=None, expected_completion_time=60,
                           base_priority=3, tags=None, location=None):
    """Composite: create_process + admit_all_processes + build_schedule + get_schedule_view(today)."""
    from datetime import datetime
    create_result = syscalls.create_process(
        name=name, process_type=process_type, deadline=deadline,
        expected_completion_time=expected_completion_time, base_priority=base_priority,
        tags=tags or [], location=location,
    )
    if not create_result.get("ok"):
        return create_result
    syscalls.admit_all_processes()
    syscalls.build_schedule()
    today = datetime.now().strftime("%Y-%m-%d")
    view_result = syscalls.get_schedule_view(today)
    return {"ok": True, "create": create_result, "today": today, "schedule_view": view_result}


# Tool name -> (description, required_args, optional_args, handler)
TOOLS = [
    (
        "max_create_process",
        "Create a new task/process (e.g. assignment, gym, meeting). Returns process_id and summary.",
        ["name"],
        ["process_type", "deadline", "expected_completion_time", "base_priority", "tags", "location"],
        lambda a: syscalls.create_process(
            name=a["name"],
            process_type=a.get("process_type", "one-time"),
            deadline=a.get("deadline"),
            expected_completion_time=a.get("expected_completion_time", 60),
            base_priority=a.get("base_priority", 3),
            tags=a.get("tags") or [],
            location=a.get("location"),
            hard_time_anchor=a.get("hard_time_anchor", False),
            preferred_time_windows=a.get("preferred_time_windows") or [],
            repeat_rule=a.get("repeat_rule"),
        ),
    ),
    (
        "max_list_processes",
        "List all processes, optionally filtered by status (new, ready, running, waiting, terminated) or by tag.",
        [],
        ["status", "tag"],
        lambda a: syscalls.list_processes(status=a.get("status"), tag=a.get("tag")),
    ),
    (
        "max_list_overdue_processes",
        "List processes that are past their deadline.",
        [],
        [],
        lambda a: syscalls.list_overdue_processes(),
    ),
    (
        "max_get_process",
        "Get a single process by id (e.g. process_1).",
        ["process_id"],
        [],
        lambda a: syscalls.get_process(a["process_id"]),
    ),
    (
        "max_remove_process",
        "Remove a process by id. Also removes it from the schedule if scheduled.",
        ["process_id"],
        [],
        lambda a: syscalls.remove_process(a["process_id"]),
    ),
    (
        "max_admit_all_processes",
        "Move all 'new' processes to 'ready' so they can be scheduled.",
        [],
        [],
        lambda a: syscalls.admit_all_processes(),
    ),
    (
        "max_load_processes",
        "Load processes from JSON file. Default path: data/processes.json.",
        [],
        ["filepath"],
        lambda a: syscalls.load_processes(filepath=a.get("filepath")),
    ),
    (
        "max_save_processes",
        "Save processes to JSON file. Default path: data/processes.json.",
        [],
        ["filepath"],
        lambda a: syscalls.save_processes(filepath=a.get("filepath")),
    ),
    (
        "max_initialize_schedule",
        "Create or reset the schedule (calendar). Default: 7 days, 06:00–00:00, 60min slots.",
        [],
        ["start_date", "end_date", "start_hour", "end_hour", "slot_duration", "schedule_name"],
        lambda a: syscalls.initialize_schedule(
            start_date=a.get("start_date"),
            end_date=a.get("end_date"),
            start_hour=a.get("start_hour", "06:00"),
            end_hour=a.get("end_hour", "00:00"),
            slot_duration=a.get("slot_duration", 60),
            schedule_name=a.get("schedule_name", "Max Schedule"),
        ),
    ),
    (
        "max_extend_schedule",
        "Add more days to the end of the schedule.",
        ["num_days"],
        [],
        lambda a: syscalls.extend_schedule(num_days=int(a.get("num_days", 1))),
    ),
    (
        "max_build_schedule",
        "Run the scheduler to assign processes to time slots (by priority and urgency).",
        [],
        [],
        lambda a: syscalls.build_schedule(),
    ),
    (
        "max_get_schedule_view",
        "Get one day's schedule: list of slots with start_time, end_time, process_id, process_name.",
        ["date"],
        [],
        lambda a: syscalls.get_schedule_view(a["date"]),
    ),
    (
        "max_get_schedule_range",
        "Get schedule for a date range. Returns days with slots.",
        ["start_date", "end_date"],
        [],
        lambda a: syscalls.get_schedule_range(a["start_date"], a["end_date"]),
    ),
    (
        "max_assign_slot",
        "Assign a process to a slot. time_or_slot_id can be '09:00' or a slot_id.",
        ["date", "time_or_slot_id", "process_id"],
        [],
        lambda a: syscalls.assign_slot(a["date"], a["time_or_slot_id"], a["process_id"]),
    ),
    (
        "max_clear_slot",
        "Clear a slot (remove assigned process).",
        ["date", "time_or_slot_id"],
        [],
        lambda a: syscalls.clear_slot(a["date"], a["time_or_slot_id"]),
    ),
    (
        "max_clear_all_assignments",
        "Clear all slot assignments; processes remain in the table.",
        [],
        [],
        lambda a: syscalls.clear_all_assignments(),
    ),
    (
        "max_get_stats",
        "Get process table and schedule statistics (counts, utilization, next deadline).",
        [],
        [],
        lambda a: syscalls.get_stats(),
    ),
    (
        "max_set_urgency_function",
        "Set scheduler urgency function: linear, exponential, or logarithmic.",
        [],
        ["function_name", "weights"],
        lambda a: syscalls.set_urgency_function(
            a.get("function_name", "linear"),
            weights=a.get("weights"),
        ),
    ),
    (
        "max_get_next_deadline",
        "Get the process with the nearest upcoming deadline.",
        [],
        [],
        lambda a: syscalls.get_next_deadline(),
    ),
    # ---- Composite workflow tools (multiple syscalls for common LLM requests) ----
    (
        "max_create_process_and_schedule",
        "Create a process, admit all new processes to ready, and run the scheduler. Use when user says 'create a task' or 'add a process' and you want the schedule updated. Returns process + build result.",
        ["name"],
        ["process_type", "deadline", "expected_completion_time", "base_priority", "tags", "location"],
        lambda a: _create_and_schedule(
            name=a["name"],
            process_type=a.get("process_type", "one-time"),
            deadline=a.get("deadline"),
            expected_completion_time=a.get("expected_completion_time", 60),
            base_priority=a.get("base_priority", 3),
            tags=a.get("tags") or [],
            location=a.get("location"),
        ),
    ),
    (
        "max_create_process_and_show_today",
        "Create a process, update the schedule, and return today's schedule. Use when user says 'create a task and show my day' or similar. Returns process + today's slots.",
        ["name"],
        ["process_type", "deadline", "expected_completion_time", "base_priority", "tags", "location"],
        lambda a: _create_and_show_today(
            name=a["name"],
            process_type=a.get("process_type", "one-time"),
            deadline=a.get("deadline"),
            expected_completion_time=a.get("expected_completion_time", 60),
            base_priority=a.get("base_priority", 3),
            tags=a.get("tags") or [],
            location=a.get("location"),
        ),
    ),
]


def _build_tool_schema(name, description, required, optional):
    """Build JSON Schema for a tool."""
    props = {}
    for arg in required + optional:
        props[arg] = {"type": "string", "description": arg.replace("_", " ")}
    # Override a few for numbers
    if "expected_completion_time" in props:
        props["expected_completion_time"]["type"] = "integer"
    if "base_priority" in props:
        props["base_priority"]["type"] = "integer"
    if "slot_duration" in props:
        props["slot_duration"]["type"] = "integer"
    if "num_days" in props:
        props["num_days"]["type"] = "integer"
    return {
        "type": "object",
        "required": required,
        "properties": props,
    }


def run_stdio():
    """Run MCP server over stdio (for Cursor, etc.)."""
    try:
        from mcp import types
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        import anyio
    except ImportError:
        print("Install MCP SDK: pip install mcp anyio", file=sys.stderr)
        sys.exit(1)

    tools_config = []
    for name, desc, required, optional, _ in TOOLS:
        tools_config.append((
            name,
            types.Tool(
                name=name,
                description=desc,
                input_schema=_build_tool_schema(name, desc, required, optional),
            ),
            required,
            optional,
        ))

    tool_handlers = {t[0]: TOOLS[i][4] for i, t in enumerate(TOOLS)}

    async def handle_list_tools(ctx, params):
        return types.ListToolsResult(tools=[t[1] for t in tools_config])

    async def handle_call_tool(ctx, params):
        name = params.name
        if name not in tool_handlers:
            return types.CallToolResult(
                content=[{"type": "text", "text": json.dumps({"ok": False, "error": f"Unknown tool: {name}"})}],
                is_error=True,
            )
        args = params.arguments or {}
        try:
            result = tool_handlers[name](args)
            return types.CallToolResult(content=_tool_result_text(result))
        except Exception as e:
            return types.CallToolResult(
                content=_tool_result_text({"ok": False, "error": str(e)}),
                is_error=True,
            )

    app = Server(
        "max",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )

    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)


if __name__ == "__main__":
    run_stdio()
