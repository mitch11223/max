"""
Example data and runner for the Max scheduler.
Creates a set of example processes, runs the scheduler, and prints the resulting
schedule and outputs. Use this to test the system and see possible results.

Run from project root:
  python -m examples.example_data
  python examples/example_data.py
"""

from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

# Ensure project root is on path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import kernel.syscalls as syscalls


def _deadline(days_from_now, time_str="23:59"):
    """Return deadline string days_from_now from today."""
    d = datetime.now() + timedelta(days=days_from_now)
    return d.strftime("%Y-%m-%d") + " " + time_str


# -----------------------------------------------------------------------------
# Example process definitions — a full day's worth (recurring + one-time)
# -----------------------------------------------------------------------------

EXAMPLE_PROCESSES = [
    # --- Morning ---
    {
        "name": "Morning Gym",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 60,
        "base_priority": 3,
        "preferred_time_windows": ["06:00"],
        "hard_time_anchor": True,
        "repeat_rule": "daily",
        "tags": ["health", "routine"],
        "location": "gym",
    },
    {
        "name": "Shower & Breakfast",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 45,
        "base_priority": 2,
        "preferred_time_windows": ["07:00"],
        "tags": ["routine"],
        "location": "home",
    },
    {
        "name": "Deep Work Block 1",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 90,
        "base_priority": 4,
        "preferred_time_windows": ["08:00"],
        "tags": ["work", "focus"],
        "location": "home",
    },
    {
        "name": "Standup / Check-in",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 30,
        "base_priority": 3,
        "preferred_time_windows": ["10:00"],
        "tags": ["work", "meeting"],
        "location": "home",
    },
    {
        "name": "COSC 3P71 Assignment",
        "process_type": "one-time",
        "deadline": _deadline(2),
        "expected_completion_time": 180,
        "base_priority": 5,
        "minimum_session_length": 60,
        "max_session_length": 120,
        "tags": ["academic", "urgent"],
        "location": "library",
    },
    {
        "name": "Doctor Appointment",
        "process_type": "one-time",
        "deadline": _deadline(1, "10:00"),
        "expected_completion_time": 60,
        "base_priority": 4,
        "tags": ["health"],
        "location": "clinic",
    },
    # --- Midday ---
    {
        "name": "Lunch Break",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 45,
        "base_priority": 2,
        "preferred_time_windows": ["12:00"],
        "repeat_rule": "daily",
        "tags": ["routine", "health"],
        "location": "home",
    },
    {
        "name": "Email & Admin",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 30,
        "base_priority": 3,
        "preferred_time_windows": ["13:00"],
        "tags": ["work", "admin"],
        "location": "home",
    },
    {
        "name": "Deep Work Block 2",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 120,
        "base_priority": 4,
        "preferred_time_windows": ["14:00"],
        "tags": ["work", "focus"],
        "location": "home",
    },
    {
        "name": "Portfolio Website",
        "process_type": "one-time",
        "deadline": _deadline(7, "17:00"),
        "expected_completion_time": 120,
        "base_priority": 3,
        "tags": ["career", "personal"],
        "location": "home",
    },
    {
        "name": "Tax Prep",
        "process_type": "one-time",
        "deadline": _deadline(5),
        "expected_completion_time": 120,
        "base_priority": 4,
        "tags": ["admin"],
        "location": "home",
    },
    # --- Afternoon / Evening ---
    {
        "name": "Walk / Fresh Air",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 30,
        "base_priority": 2,
        "preferred_time_windows": ["17:00"],
        "tags": ["health", "routine"],
        "location": "outdoor",
    },
    {
        "name": "Dinner",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 45,
        "base_priority": 2,
        "preferred_time_windows": ["18:00"],
        "tags": ["routine", "health"],
        "location": "home",
    },
    {
        "name": "Study Session",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 90,
        "base_priority": 4,
        "preferred_time_windows": ["19:00"],
        "tags": ["academic"],
        "location": "library",
    },
    {
        "name": "Reading",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 45,
        "base_priority": 2,
        "preferred_time_windows": ["21:00"],
        "tags": ["personal"],
        "location": "home",
    },
    {
        "name": "Wind Down / Sleep Prep",
        "process_type": "recurring",
        "deadline": None,
        "expected_completion_time": 30,
        "base_priority": 2,
        "preferred_time_windows": ["22:00"],
        "tags": ["routine", "health"],
        "location": "home",
    },
]


def _format_next_deadline(nd):
    """Turn next_deadline dict into a single readable line."""
    if not nd or not isinstance(nd, dict):
        return "None"
    name = nd.get("name", "?")
    dl = nd.get("deadline")
    return f"{name} — {dl}" if dl else name


def _format_status_counts(by_status):
    """Turn status dict into 'X new, Y ready, Z running, ...'."""
    if not isinstance(by_status, dict):
        return str(by_status)
    order = ("new", "ready", "running", "waiting", "terminated")
    parts = [f"{by_status.get(s, 0)} {s}" for s in order if by_status.get(s, 0) != 0]
    return ", ".join(parts) if parts else "0"


def _print_stats(stats):
    """Print stats in human-readable form (no raw dicts)."""
    print("\n" + "-" * 60)
    print("STATS")
    print("-" * 60)
    print(f"  Processes: {stats.get('process_count', 0)}")
    print(f"  By status: {_format_status_counts(stats.get('process_count_by_status', {}))}")
    print(f"  Total remaining time: {stats.get('total_remaining_time_min', 0)} min")
    print(f"  Next deadline: {_format_next_deadline(stats.get('next_deadline'))}")
    print(f"  Schedule days: {stats.get('schedule_day_count', 0)}")
    print(f"  Free time: {stats.get('schedule_total_free_time_min', 0)} min")
    print(f"  Scheduled time: {stats.get('schedule_total_scheduled_time_min', 0)} min")
    print(f"  Utilization: {stats.get('schedule_utilization_rate', 0)}%")


def _print_schedule_by_day(schedule_by_date):
    """Print schedule as a clear timeline; show every slot; empty slots show 'Empty'."""
    print("\n" + "-" * 60)
    print("SCHEDULE BY DAY")
    print("-" * 60)
    for date in sorted(schedule_by_date.keys()):
        view = schedule_by_date[date]
        if not view.get("ok"):
            print(f"\n  {date}: (no data)")
            continue
        slots = view.get("slots", [])
        print(f"\n  {date}:")
        if not slots:
            print("    (no slots)")
            continue
        for slot in slots:
            start = slot.get("start_time", "?")
            end = slot.get("end_time", "?")
            name = slot.get("process_name") or "Empty"
            print(f"    {start}-{end}  {name}")


def run_example(
    start_date=None,
    end_date=None,
    start_hour="06:00",
    end_hour="00:00",
    slot_duration=30,
    print_days=True,
    print_stats=True,
    print_json=False,
):
    """
    Create example processes, run the scheduler, and optionally print schedule and stats.

    Returns dict with:
      processes_created: list of create_process results
      build_result: from build_schedule()
      stats: from get_stats()
      schedule_by_date: {date: get_schedule_view(date)} for each day
      schedule_range: get_schedule_range(start_date, end_date)

    Set print_json=True to also print the full output as JSON.
    """
    if start_date is None:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if end_date is None:
        end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    # Start fresh: clear processes and schedule, then initialize
    syscalls.reset_state()

    # Initialize schedule (creates fresh schedule + dispatcher)
    syscalls.initialize_schedule(
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour,
        slot_duration=slot_duration,
        schedule_name="Example Schedule",
    )

    # Create all example processes
    created = []
    for spec in EXAMPLE_PROCESSES:
        # Copy so we don't mutate the original
        s = dict(spec)
        r = syscalls.create_process(
            name=s["name"],
            process_type=s.get("process_type", "one-time"),
            deadline=s.get("deadline"),
            expected_completion_time=s.get("expected_completion_time", 60),
            base_priority=s.get("base_priority", 3),
            preferred_time_windows=s.get("preferred_time_windows"),
            hard_time_anchor=s.get("hard_time_anchor", False),
            repeat_rule=s.get("repeat_rule"),
            tags=s.get("tags") or [],
            location=s.get("location"),
            minimum_session_length=s.get("minimum_session_length"),
            max_session_length=s.get("max_session_length"),
        )
        if r.get("ok"):
            created.append(r)

    # Admit and build
    syscalls.admit_all_processes()
    build_result = syscalls.build_schedule()

    # Gather outputs
    stats = syscalls.get_stats()
    schedule_range = syscalls.get_schedule_range(start_date, end_date)
    schedule_by_date = {}
    for date in sorted(schedule_range.get("days", {}).keys()):
        schedule_by_date[date] = syscalls.get_schedule_view(date)

    # Optional printing
    if print_days or print_stats or print_json:
        print("\n" + "=" * 60)
        print("EXAMPLE SCHEDULE RUN")
        print("=" * 60)
        print(f"Period: {start_date} to {end_date}")
        print(f"Processes created: {len(created)}")
        print(f"Build: scheduled_count={build_result.get('scheduled_count')}, utilization={build_result.get('utilization_rate')}%")

    if print_stats:
        _print_stats(stats)

    if print_days:
        _print_schedule_by_day(schedule_by_date)

    if print_json:
        print("\n" + "-" * 60)
        print("FULL OUTPUT (JSON)")
        print("-" * 60)
        out = {
            "build_result": build_result,
            "stats": stats,
            "schedule_by_date": {
                d: {"ok": v.get("ok"), "date": v.get("date"), "slots": v.get("slots", [])}
                for d, v in schedule_by_date.items()
            },
        }
        print(json.dumps(out, indent=2, default=str))

    return {
        "processes_created": created,
        "build_result": build_result,
        "stats": stats,
        "schedule_by_date": schedule_by_date,
        "schedule_range": schedule_range,
    }


if __name__ == "__main__":
    run_example(print_days=True, print_stats=True, print_json=False)
    print("\nDone.")
