# Examples

## example_data

Loads example process definitions, runs the scheduler via `kernel.syscalls`, and prints the resulting schedule and stats. Use it to test the system and see possible outputs.

**Run from project root:**

```bash
python3 -m examples.example_data
# or
python3 examples/example_data.py
```

**What it does:**

1. Resets state (`syscalls.reset_state()`).
2. Initializes a 7-day schedule (06:00–00:00, 60 min slots).
3. Creates 8 example processes (gym, assignments, lunch, study, doctor, reading, tax).
4. Admits all and runs `build_schedule()`.
5. Prints stats and schedule-by-day; optionally prints full JSON.

**Programmatic use:**

```python
from examples.example_data import run_example, EXAMPLE_PROCESSES

# Run with default 7-day window, print days + stats
result = run_example(print_days=True, print_stats=True)

# Run and get structured output (no print)
result = run_example(print_days=False, print_stats=False)
# result["schedule_by_date"], result["stats"], result["build_result"], etc.

# Include full JSON in stdout
run_example(print_json=True)

# Custom date range
run_example(start_date="2026-03-01", end_date="2026-03-14")
```

**Possible outputs:** The return value includes `processes_created`, `build_result`, `stats`, `schedule_by_date` (per-day slot list), and `schedule_range` (full range). Stats include process counts, utilization, next deadline. Schedule slots include `start_time`, `end_time`, `process_id`, `process_name`.
