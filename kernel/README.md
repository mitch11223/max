# Kernel

Core scheduling: **kernel.py** (implementation) and **syscalls.py** (syscall layer). External code (MCP server, CLI, scripts) should use **kernel.syscalls** only; do not import kernel classes directly.

## Components

- **kernel.py** — TimeSlot, Day, Process, ProcessTable, Schedule, Dispatcher (internal).
- **syscalls.py** — Syscall layer; owns the single ProcessTable, Schedule, Dispatcher; exposes functions that return JSON-serializable data. This is the only module that imports kernel.py.

## Usage (syscalls — recommended)

From project root (`max/`):

```python
import kernel.syscalls as syscalls

syscalls.create_process(name="Gym", expected_completion_time=60)
syscalls.admit_all_processes()
syscalls.build_schedule()
print(syscalls.get_schedule_view("2025-03-02"))
```

## Usage (direct kernel — for demos only)

```python
from kernel import Process, ProcessTable, Schedule, Dispatcher

pt = ProcessTable()
schedule = Schedule()
schedule.initialize()
dispatcher = Dispatcher(pt, schedule)
dispatcher.build_schedule()
```

```bash
python3 -m kernel.sample_usage
```

## Data Storage

API uses `data/processes.json` (at project root) by default.