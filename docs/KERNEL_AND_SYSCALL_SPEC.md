# Kernel and Syscall Specification

This document specifies every class, attribute, and method in the Max kernel (`kernel/kernel.py`), and the syscall layer in **kernel/syscalls.py**. It also indicates which syscalls map directly to kernel methods and which are composite, and how orchestration (e.g. “create a process then update the schedule then render”) works.

---

## 1. Kernel classes (internal)

Only the syscall layer (**kernel/syscalls.py**) should import and use these. No other code should depend on kernel types directly.

---

### 1.1 TimeSlot

**Role:** A single time block (start time, end time) that can hold one Process or be free.

| Item | Type | Description |
|------|------|-------------|
| **Constructor** | `TimeSlot(start_time: str, end_time: str, slot_id: str)` | Times in `"HH:MM"`; `slot_id` is a unique identifier. |
| **_start_time** | (attr) | str, `"HH:MM"` |
| **_end_time** | (attr) | str, `"HH:MM"` |
| **_assigned_process** | (attr) | Process or None |
| **_slot_id** | (attr) | str |
| **_duration** | (attr) | int, minutes (computed) |
| **get_slot_id()** | method | → str |
| **_calculate_duration()** | method | (internal) → int |
| **get_duration()** | method | → int |
| **get_process()** | method | → Process or None |
| **get_start_time()** | method | → str |
| **get_end_time()** | method | → str |
| **assign_process(process)** | method | void |
| **clear_process()** | method | void |
| **__repr__()** | method | → str |

**Not exposed via syscalls:** TimeSlot is used only inside Day/Schedule. No direct syscall; schedule views serialize slots via Schedule/Day.

---

### 1.2 Day

**Role:** One calendar date with a grid of TimeSlots from start_hour to end_hour.

| Item | Type | Description |
|------|------|-------------|
| **Constructor** | `Day(date: str, start_hour: str, end_hour: str, slot_duration: int)` | `date` = `"YYYY-MM-DD"`; duration in minutes. |
| **_date** | (attr) | str |
| **_start_hour** | (attr) | str `"HH:MM"` |
| **_end_hour** | (attr) | str `"HH:MM"` |
| **_slot_duration** | (attr) | int |
| **_timeslots** | (attr) | dict[str, TimeSlot] |
| **_generate_timeslots()** | method | (internal) void |
| **get_date()** | method | → str |
| **get_timeslots(status=None)** | method | status: None \| "free" \| "occupied" → dict[str, TimeSlot] |
| **get_slot(identifier)** | method | identifier = slot_id or time `"HH:MM"` → TimeSlot or None |
| **clear_timeslots(identifier=None)** | method | None = all; else one slot. void |
| **get_timeslot_count(status=None)** | method | → int |
| **get_total_free_time()** | method | → int (minutes) |
| **__repr__()** | method | → str |

**Not exposed via syscalls:** Day is used only inside Schedule. Syscalls use Schedule methods that return day data (see get_schedule_view / get_schedule_range).

---

### 1.3 Process

**Role:** One task (PCB-like): identity, timing, priority, state, preferences.

| Item | Type | Description |
|------|------|-------------|
| **Constructor** | `Process(name, process_type, process_id, deadline, expected_completion_time, base_priority, preferred_time_windows=None, hard_time_anchor=False, preferred_days=None, repeat_rule=None, outside_peak_multiplier=1.0, peak_multiplier=1.0, repeat_end_date=None, minimum_session_length=1, max_session_length=None, split_across_day=True, tags=None, location=None, dependencies=None)` | Many optional args; see kernel. |
| **_name** | (attr) | str |
| **_type** | (attr) | str (e.g. "one-time", "recurring") |
| **_id** | (attr) | str (e.g. "process_1") |
| **_deadline** | (attr) | str `"YYYY-MM-DD HH:MM"` or None |
| **_expected_completion_time** | (attr) | int (minutes) |
| **_remaining_time** | (attr) | int |
| **_created_at** | (attr) | datetime |
| **_base_priority** | (attr) | number |
| **_current_priority** | (attr) | number |
| **_aging_counter** | (attr) | int |
| **_preferred_time_windows** | (attr) | list |
| **_hard_time_anchor** | (attr) | bool |
| **_preferred_days** | (attr) | list |
| **_repeat_rule** | (attr) | str or None |
| **_repeat_end_date** | (attr) | str or None |
| **_outside_peak_multiplier** | (attr) | float |
| **_peak_multiplier** | (attr) | float |
| **_minimum_session_length** | (attr) | int |
| **_max_session_length** | (attr) | int or None |
| **_split_across_day** | (attr) | bool |
| **_status** | (attr) | "new" \| "ready" \| "running" \| "waiting" \| "terminated" |
| **_last_scheduled_date** | (attr) | str or None |
| **_total_time_logged** | (attr) | int |
| **_tags** | (attr) | list[str] |
| **_location** | (attr) | str or None |
| **_dependencies** | (attr) | list[str] (process ids) |
| **get_name()** … **get_dependencies()** | methods | Getters for all above (21 getters) |
| **set_name(name)** … **set_dependencies(dependencies)** | methods | Setters for mutable fields (20 setters) |
| **admit()** | method | new → ready |
| **dispatch()** | method | ready → running |
| **interrupt()** | method | running → ready |
| **wait()** | method | running → waiting |
| **wake_up()** | method | waiting → ready |
| **exit()** | method | running → terminated, remaining_time=0 |
| **is_ready()**, **is_running()**, **is_waiting()**, **is_terminated()** | methods | → bool |
| **is_overdue()** | method | → bool |
| **calculate_deadline_urgency()** | method | → number |
| **calculate_current_priority()** | method | → number |
| **increment_aging_counter()** | method | void |
| **reset_aging_counter()** | method | void |
| **log_time(minutes)** | method | void |
| **get_time_until_deadline()** | method | → int (minutes) or None |
| **__repr__()** | method | → str |

**Syscall mapping:** Process is not constructed by API callers; API creates processes via ProcessTable.create_process and returns serialized dicts (get_process, list_processes, get_next_deadline).

---

### 1.4 ProcessTable

**Role:** Container for all Process objects; creation, lookup, filtering, persistence.

| Item | Type | Description |
|------|------|-------------|
| **Constructor** | `ProcessTable()` | No args. |
| **_processes** | (attr) | dict[str, Process] |
| **_next_id** | (attr) | int |
| **create_process(...)** | method | Full Process constructor args → Process. Auto-assigns process_id. |
| **add_process(process)** | method | void |
| **remove_process(process_id)** | method | void |
| **get_process(process_id)** | method | → Process or None |
| **get_all_processes()** | method | → dict[str, Process] |
| **get_processes_by_status(status)** | method | → dict |
| **get_processes_by_tag(tag)** | method | → dict |
| **get_ready_processes()** | method | → dict |
| **get_overdue_processes()** | method | → dict |
| **get_processes_by_location(location)** | method | → dict |
| **get_processes_by_deadline_range(start_date, end_date)** | method | → dict |
| **update_all_priorities()** | method | void |
| **increment_all_aging()** | method | void |
| **admit_all_new()** | method | void |
| **check_dependencies_met(process_id)** | method | → bool |
| **get_blocked_processes()** | method | → dict |
| **get_processes_depending_on(process_id)** | method | → dict |
| **get_process_count(status=None)** | method | → int |
| **get_total_remaining_time()** | method | → int |
| **get_average_priority()** | method | → float |
| **get_next_deadline()** | method | → Process or None |
| **get_stale_processes(aging_threshold=10)** | method | → dict |
| **save_to_json(filepath)** | method | void |
| **load_from_json(filepath)** | method | void |
| **clear_all()** | method | void |
| **__repr__()** | method | → str |

---

### 1.5 Schedule

**Role:** Calendar of Days; slot access, assignment, conflicts, stats.

| Item | Type | Description |
|------|------|-------------|
| **Constructor** | `Schedule(schedule_name="My Schedule")` | |
| **_schedule_id** | (attr) | str (auto) |
| **_schedule_name** | (attr) | str |
| **_days** | (attr) | dict[str, Day] |
| **_start_date**, **_end_date** | (attr) | str or None |
| **_working_hours** | (attr) | (start_hour, end_hour) |
| **_slot_duration** | (attr) | int |
| **_created_at**, **_last_updated** | (attr) | datetime |
| **initialize(...)** | method | start_date, end_date, start_hour, end_hour, slot_duration → void |
| **refresh()** | method | Re-initialize with same params. void |
| **extend(num_days)** | method | void |
| **get_day(date)** | method | → Day or None |
| **get_all_days()** | method | → dict |
| **get_days_range(start_date, end_date)** | method | → dict |
| **get_today()**, **get_tomorrow()** | methods | → Day or None |
| **get_next_n_days(n)** | method | → dict |
| **get_slot(date, identifier)** | method | → TimeSlot or None |
| **get_all_free_slots()** | method | → dict |
| **get_free_slots_on_date(date)** | method | → dict |
| **find_slot_by_process(process_id)** | method | → (date, slot_id, slot) or None |
| **get_slots_in_time_window(start_time, end_time)** | method | → dict |
| **assign_process_to_slot(date, slot_identifier, process)** | method | void |
| **clear_slot(date, slot_identifier)** | method | void |
| **clear_all_assignments()** | method | void |
| **clear_day(date)** | method | void |
| **remove_process_from_schedule(process_id)** | method | void |
| **check_conflicts()** | method | → list of conflict dicts |
| **has_conflict_at(date, time)** | method | → bool |
| **validate_schedule()** | method | → bool |
| **get_total_free_time()** | method | → int |
| **get_total_scheduled_time()** | method | → int |
| **get_scheduled_process_count()** | method | → int |
| **get_day_count()** | method | → int |
| **get_utilization_rate()** | method | → float |
| **get_daily_breakdown()** | method | → dict |
| **print_day(date)** | method | void (stdout) |
| **print_full_schedule()** | method | void (stdout) |
| **export_to_dict()** | method | → dict (JSON-serializable) |
| **get_schedule_id()**, **get_schedule_name()**, **set_schedule_name(name)** | methods | |
| **get_created_at()**, **get_last_updated()**, **update_timestamp()** | methods | |
| **__repr__()** | method | → str |

---

### 1.6 Dispatcher

**Role:** Multi-level queue scheduler; assigns ProcessTable’s processes to Schedule’s slots.

| Item | Type | Description |
|------|------|-------------|
| **Constructor** | `Dispatcher(process_table, schedule, urgency_function="linear", weights=None)` | |
| **_process_table** | (attr) | ProcessTable |
| **_schedule** | (attr) | Schedule |
| **_urgency_function_name** | (attr) | str |
| **_weights** | (attr) | dict |
| **_queues** | (attr) | dict[int, list[Process]] (5 queues) |
| **_urgency_functions** | (attr) | dict of callables |
| **_calculate_linear_urgency(process)** | method | (internal) → number |
| **_calculate_exponential_urgency(process)** | method | (internal) → number |
| **_calculate_logarithmic_urgency(process)** | method | (internal) → number |
| **calculate_urgency(process)** | method | → number |
| **assign_to_queue(process)** | method | → int (1–5) |
| **populate_queues()** | method | void |
| **refresh_urgency()** | method | void |
| **_fits_time_window(process, slot)** | method | (internal) → bool |
| **_check_dependencies_met(process)** | method | (internal) → bool |
| **_find_best_slot_for_process(process, date=None)** | method | (internal) → (date, slot_id, slot) or None |
| **schedule_hard_anchors()** | method | void |
| **schedule_flexible_tasks()** | method | void |
| **distribute_task_across_days(process)** | method | void |
| **handle_preemption(new_process)** | method | → bool |
| **build_schedule()** | method | void (main entry) |
| **set_urgency_function(function_name, weights=None)** | method | void |
| **set_weights(weights)** | method | void |
| **get_queue_contents()** | method | → dict[int, list[str]] (names) |
| **__repr__()** | method | → str |

---

## 2. Who orchestrates “create process → update schedule → render”?

A question like *“create a process”* or *“add a task and show my day”* needs **multiple syscalls**: e.g. create_process, then admit_all_processes, then build_schedule, then get_schedule_view to return data. That orchestration can live at two levels:

1. **LLM level (granular tools)**  
   The MCP server exposes **one tool per syscall**. The LLM has the schema for all tools and decides the sequence: e.g. call `max_create_process`, then `max_build_schedule`, then `max_get_schedule_view`. So “create a process, then update the schedule, then render” is **orchestrated by the LLM** via multiple tool calls.

2. **MCP server level (composite tools)**  
   The MCP server can also expose **workflow tools** that call several syscalls internally and return a combined result. For example:
   - **max_create_process_and_schedule** → create_process + admit_all_processes + build_schedule (one tool call for “create and update schedule”).
   - **max_create_process_and_show_today** → create_process + admit_all_processes + build_schedule + get_schedule_view(today) (one tool call for “create and show my day”).

So the abstraction level for “create then update then render” is **either** the LLM (using granular tools) **or** the MCP server (using composite workflow tools). The syscall layer (kernel/syscalls.py) stays a single-syscall layer; composite behavior is only in the MCP server.

---

## 3. Syscalls (kernel/syscalls.py)

All return JSON-serializable dicts (or list/dict) unless noted. The API holds a single ProcessTable, Schedule, and Dispatcher; callers never receive kernel objects.

---

### 2.1 Process syscalls

| Syscall | Kernel mapping | Direct? | Notes |
|---------|----------------|--------|-------|
| **create_process(...)** | ProcessTable.create_process(...) | **Yes** | API forwards args and returns serialized process dict. |
| **get_process(process_id)** | ProcessTable.get_process(process_id) | **Yes** | API serializes Process → dict. |
| **list_processes(status=None, tag=None)** | ProcessTable.get_all_processes() or get_processes_by_status(status) or get_processes_by_tag(tag) | **Yes** | Optional filter by tag (e.g. "work"). |
| **list_overdue_processes()** | ProcessTable.get_overdue_processes() | **Yes** | Returns list of process dicts past deadline. |
| **remove_process(process_id)** | ProcessTable.get_process + Schedule.remove_process_from_schedule + ProcessTable.remove_process | **Composite** | Ensures schedule exists; removes from schedule then table. |
| **admit_all_processes()** | ProcessTable.admit_all_new() | **Yes** | |

---

### 2.2 Persistence syscalls

| Syscall | Kernel mapping | Direct? | Notes |
|---------|----------------|--------|-------|
| **load_processes(filepath=None)** | ProcessTable.load_from_json(path) | **Yes** | Default path: data/processes.json. |
| **save_processes(filepath=None)** | ProcessTable.save_to_json(path) | **Yes** | Creates parent dir if needed. |

---

### 2.3 Schedule syscalls

| Syscall | Kernel mapping | Direct? | Notes |
|---------|----------------|--------|-------|
| **initialize_schedule(...)** | Schedule() + Schedule.initialize(...); Dispatcher(...) | **Composite** | Creates global Schedule and Dispatcher. |
| **build_schedule()** | Dispatcher.build_schedule() | **Yes** | |
| **get_schedule_view(date)** | Schedule.get_day(date) + Day.get_timeslots() + serialize each slot | **Composite** | Returns { ok, date, slots: [{ slot_id, start_time, end_time, duration_min, process_id, process_name }] }. |
| **get_schedule_range(start_date, end_date)** | Schedule.get_days_range() + for each day serialize slots | **Composite** | Returns { ok, days: { date: [ slots ] } }. |
| **assign_slot(date, time_or_slot_id, process_id)** | ProcessTable.get_process + Schedule.get_slot + Schedule.assign_process_to_slot | **Composite** | Resolves process and slot; then single kernel call for assign. |
| **clear_slot(date, time_or_slot_id)** | Schedule.clear_slot(date, time_or_slot_id) | **Yes** | After _ensure_schedule(). |
| **clear_all_assignments()** | Schedule.clear_all_assignments() | **Yes** | |
| **extend_schedule(num_days)** | Schedule.extend(num_days) | **Yes** | Add days to end of schedule. |

---

### 2.4 Stats / config syscalls

| Syscall | Kernel mapping | Direct? | Notes |
|---------|----------------|--------|-------|
| **get_stats()** | ProcessTable (counts, total_remaining_time, average_priority, get_next_deadline) + Schedule (day_count, free/scheduled time, utilization, scheduled_process_count) | **Composite** | Single dict aggregating both. |
| **set_urgency_function(function_name, weights=None)** | Dispatcher.set_urgency_function(...) | **Yes** | |
| **get_next_deadline()** | ProcessTable.get_next_deadline() | **Yes** | API serializes Process → dict. |

---

## 4. Summary: direct vs composite syscalls

- **Direct syscalls** (1:1 or simple wrapper with serialization):  
  `create_process`, `get_process`, `list_processes`, `list_overdue_processes`, `admit_all_processes`, `load_processes`, `save_processes`, `build_schedule`, `extend_schedule`, `clear_slot`, `clear_all_assignments`, `set_urgency_function`, `get_next_deadline`.

- **Composite syscalls** (multiple kernel calls or formatting):  
  `remove_process`, `initialize_schedule`, `get_schedule_view`, `get_schedule_range`, `assign_slot`, `get_stats`.

---

## 5. MCP tools → syscalls and composite workflows

The MCP server (`mcp_servers/max_server.py`) exposes:

- **Granular tools** — one tool = one API syscall (and one or more kernel calls as in the tables above).
- **Composite workflow tools** — one tool = multiple syscalls, for common LLM requests like “create a task and show my day.”

| MCP tool | API syscall(s) | Notes |
|----------|----------------|-------|
| max_create_process | create_process | |
| max_list_processes | list_processes | optional status, tag |
| max_list_overdue_processes | list_overdue_processes | |
| max_get_process | get_process | |
| max_remove_process | remove_process | |
| max_admit_all_processes | admit_all_processes | |
| max_load_processes | load_processes | |
| max_save_processes | save_processes | |
| max_initialize_schedule | initialize_schedule | |
| max_extend_schedule | extend_schedule | |
| max_build_schedule | build_schedule | |
| max_get_schedule_view | get_schedule_view | |
| max_get_schedule_range | get_schedule_range | |
| max_assign_slot | assign_slot | |
| max_clear_slot | clear_slot | |
| max_clear_all_assignments | clear_all_assignments | |
| max_get_stats | get_stats | |
| max_set_urgency_function | set_urgency_function | |
| max_get_next_deadline | get_next_deadline | |
| **max_create_process_and_schedule** | create_process + admit_all_processes + build_schedule | **Composite** — “create and update schedule” in one call. |
| **max_create_process_and_show_today** | create_process + admit_all_processes + build_schedule + get_schedule_view(today) | **Composite** — “create and show my day” in one call. |

So the mapping from MCP tool to kernel is: **MCP tool → one or more API syscalls → one or more kernel methods** as specified in the tables above.

---

## 6. Agents layer (agents/)

The agents layer sits **above** the syscall layer. It is the autonomous execution
tier: where natural language goals become running work.

### Architecture stack

```
User goal (natural language)
    ↓
AgentOrchestrator          agents/orchestrator.py
    ↓  (syscalls only)
kernel/syscalls.py
    ↓  (kernel objects)
kernel/kernel.py
```

**Rule:** Agents import from `kernel.syscalls` only. They never import
`kernel.kernel` directly. This mirrors the rule that syscalls.py is the only
kernel consumer.

---

### 6.1 Process vs Agent — the key distinction

| | Process | Agent |
|---|---|---|
| **What it is** | Kernel data record (PCB-like) | Autonomous executor |
| **Lives in** | `ProcessTable` (kernel) | `_active_agents` (orchestrator) |
| **Knows** | Priority, deadline, status, time | LLM client, tools, logic |
| **Does** | Gets scheduled into TimeSlots | Actually performs the task |
| **Lifecycle** | new → ready → running → terminated | initialized → running → completed/failed |

An Agent holds a `process_id`. When it starts, the process becomes `running`.
When it finishes, it calls `remove_process(process_id)` and the process is
removed from the kernel. **An Agent is not a Process subclass** — they are
separate concerns linked by ID.

---

### 6.2 AgentOrchestrator

**File:** `agents/orchestrator.py`

| Method | Description |
|--------|-------------|
| `process_goal(user_input, context)` | Main entry point. Decomposes goal → processes → agents. Returns plan + schedule. |
| `handle_agent_update(agent_id, progress)` | Called by agents to report progress or completion. |
| `_decompose_goal(user_input, context)` | LLM call → structured JSON plan with tasks. |
| `_create_processes_from_plan(plan)` | Creates kernel Processes from plan via syscalls. Returns list of process_ids. |
| `_spawn_agents_for_processes(process_ids)` | Instantiates correct Agent subclass for each process. |
| `_spawn_agent(agent_type, process_id, parent_id)` | Instantiates one Agent. Internal + used by CoordinationAgent via base_agent. |
| `_determine_agent_type(process_dict)` | Reads process tags to pick agent type. First matching tag wins. |
| `get_active_agents()` | Returns list of active agent summaries. |
| `get_execution_log()` | Returns full orchestrator event log. |

---

### 6.3 Agent base class

**File:** `agents/base_agent.py`

| Method | Description |
|--------|-------------|
| `execute()` | Override in subclass. Must call `complete()` or `fail()`. |
| `complete(result)` | Removes process from kernel, logs completion, notifies orchestrator. |
| `fail(reason)` | Logs failure, notifies orchestrator. Process stays for inspection. |
| `report_progress(progress)` | Sends interim update to orchestrator. |
| `spawn_child(agent_type, process_id)` | Delegates to orchestrator to spawn a sub-agent. Used by CoordinationAgent. |

---

### 6.4 Agent types

| Type | Class | Tag | Use case |
|------|-------|-----|----------|
| Research | `ResearchAgent` | `research` | Web search, document analysis, fact-finding |
| Transaction | `TransactionAgent` | `transaction` | Purchases, bookings, payments, orders |
| Communication | `CommunicationAgent` | `communication` | Email, messaging, calendar scheduling |
| Organization | `OrganizationAgent` | `organization` | File management, notes, archiving |
| Creation | `CreationAgent` | `creation` | Code, documents, designs, any new artifact |
| Analysis | `AnalysisAgent` | `analysis` | Data analysis, comparison, recommendations |
| Monitoring | `MonitoringAgent` | `monitoring` | Event watching, triggers, deadline alerts |
| Coordination | `CoordinationAgent` | `coordination` | Multi-agent workflows; spawns child agents |

Agent type is determined by the **first process tag** that matches a known type.
Tags are set by `_decompose_goal` via the LLM.

---

### 6.5 Typical flow

```
orchestrator.process_goal("Plan trip to Japan in May")
    → _decompose_goal()         # LLM breaks into 5 tasks
    → _create_processes_from_plan()  # 5 kernel Processes created
    → admit_all_processes()     # new → ready
    → build_schedule()          # Dispatcher assigns to TimeSlots
    → _spawn_agents_for_processes()  # 5 Agents instantiated
    → [caller runs agent.execute() per agent]
        ResearchAgent.execute()     → finds visa info, flights, hotels
        AnalysisAgent.execute()     → ranks options
        TransactionAgent.execute()  → books flights + hotel
        CommunicationAgent.execute()→ sends itinerary email
        OrganizationAgent.execute() → saves trip folder with docs
```
