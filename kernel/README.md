# Kernel

Core scheduling logic in a single module: `kernel.py` (monolithic kernel).

## Components (all in `kernel.py`)

- **TimeSlot** — Single time block (start, end, optional Process)
- **Day** — One date with a grid of TimeSlots
- **Process** — Task (PCB-like: deadline, priority, state)
- **ProcessTable** — Container for all Process objects; JSON persistence
- **Schedule** — Calendar of Days
- **Dispatcher** — Assigns Processes to TimeSlots (multi-level queue, urgency)

## Usage

From project root (`max/`):

```bash
python3 -m kernel.sample_usage
```

```python
from kernel import Process, ProcessTable, Schedule, Dispatcher

pt = ProcessTable()
schedule = Schedule()
schedule.initialize()
dispatcher = Dispatcher(pt, schedule)
dispatcher.build_schedule()
```

## Data Storage

ProcessTable uses JSON (`data/processes.json`) for persistence.

## Independence

Framework-agnostic; no dependency on MCP or OpenClaw.