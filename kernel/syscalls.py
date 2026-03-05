# Max syscalls — syscall-style layer over the kernel.
# This module is the only place that imports kernel implementation. All callers (MCP server, CLI, etc.)
# use this module only. Returns JSON-serializable data.

import os
from pathlib import Path

from .kernel import ProcessTable, Schedule, Dispatcher

# -----------------------------------------------------------------------------
# Single "world" state (syscalls module owns the references to kernel objects)
# -----------------------------------------------------------------------------

_process_table = ProcessTable()
_schedule = None  # created on initialize_schedule
_dispatcher = None
# Data path at project root (parent of kernel/)
_default_data_path = Path(__file__).resolve().parent.parent / "data" / "processes.json"


def _ensure_schedule():
    """Ensure schedule and dispatcher exist; create with defaults if not."""
    global _schedule, _dispatcher
    if _schedule is None:
        _schedule = Schedule(schedule_name="Max Schedule")
        _schedule.initialize()
        _dispatcher = Dispatcher(_process_table, _schedule)
    return _schedule, _dispatcher


def _process_to_dict(p):
    """Serialize a Process to a plain dict (no kernel objects)."""
    if p is None:
        return None
    return {
        "id": p.get_id(),
        "name": p.get_name(),
        "type": p.get_type(),
        "deadline": p.get_deadline(),
        "expected_completion_time": p.get_expected_completion_time(),
        "remaining_time": p.get_remaining_time(),
        "base_priority": p.get_base_priority(),
        "current_priority": p.get_current_priority(),
        "status": p.get_status(),
        "tags": p.get_tags(),
        "location": p.get_location(),
        "created_at": p.get_created_at().strftime("%Y-%m-%d %H:%M:%S") if p.get_created_at() else None,
    }


# -----------------------------------------------------------------------------
# Process syscalls
# -----------------------------------------------------------------------------

def create_process(
    name,
    process_type="one-time",
    deadline=None,
    expected_completion_time=60,
    base_priority=3,
    preferred_time_windows=None,
    hard_time_anchor=False,
    preferred_days=None,
    repeat_rule=None,
    repeat_end_date=None,
    minimum_session_length=1,
    max_session_length=None,
    split_across_day=True,
    tags=None,
    location=None,
    dependencies=None,
):
    """Create a new process. Returns dict with id and summary."""
    p = _process_table.create_process(
        name=name,
        process_type=process_type,
        deadline=deadline,
        expected_completion_time=expected_completion_time,
        base_priority=base_priority,
        preferred_time_windows=preferred_time_windows or [],
        hard_time_anchor=hard_time_anchor,
        preferred_days=preferred_days or [],
        repeat_rule=repeat_rule,
        repeat_end_date=repeat_end_date,
        minimum_session_length=minimum_session_length if minimum_session_length is not None else 1,
        max_session_length=max_session_length,
        split_across_day=split_across_day,
        tags=tags or [],
        location=location,
        dependencies=dependencies or [],
    )
    return {"ok": True, "process_id": p.get_id(), "process": _process_to_dict(p)}


def get_process(process_id):
    """Get one process by id. Returns dict or None."""
    p = _process_table.get_process(process_id)
    return _process_to_dict(p)


def list_processes(status=None, tag=None):
    """List all processes. Filter by status and/or tag. Returns list of dicts."""
    if status is not None:
        processes = _process_table.get_processes_by_status(status)
    elif tag is not None:
        processes = _process_table.get_processes_by_tag(tag)
    else:
        processes = _process_table.get_all_processes()
    return [_process_to_dict(p) for p in processes.values()]


def list_overdue_processes():
    """List processes past their deadline. Returns list of dicts."""
    processes = _process_table.get_overdue_processes()
    return [_process_to_dict(p) for p in processes.values()]


def remove_process(process_id):
    """Remove a process by id. Returns ok/error dict."""
    if _process_table.get_process(process_id) is None:
        return {"ok": False, "error": f"Process {process_id} not found"}
    if _schedule is not None:
        _schedule.remove_process_from_schedule(process_id)
    _process_table.remove_process(process_id)
    return {"ok": True}


def admit_all_processes():
    """Move all 'new' processes to 'ready'. Returns ok dict."""
    _process_table.admit_all_new()
    return {"ok": True}


# -----------------------------------------------------------------------------
# Persistence syscalls
# -----------------------------------------------------------------------------

def load_processes(filepath=None):
    """Load processes from JSON file. Returns ok/error dict."""
    path = str(filepath or _default_data_path)
    try:
        _process_table.load_from_json(path)
        return {"ok": True, "path": path, "count": _process_table.get_process_count()}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}


def save_processes(filepath=None):
    """Save processes to JSON file. Returns ok/error dict."""
    path = str(filepath or _default_data_path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _process_table.save_to_json(path)
        return {"ok": True, "path": path, "count": _process_table.get_process_count()}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}


# -----------------------------------------------------------------------------
# Schedule syscalls
# -----------------------------------------------------------------------------

def initialize_schedule(
    start_date=None,
    end_date=None,
    start_hour="06:00",
    end_hour="00:00",
    slot_duration=60,
    schedule_name="Max Schedule",
):
    """Create or reset the schedule (calendar of days). Returns ok dict."""
    global _schedule, _dispatcher
    _schedule = Schedule(schedule_name=schedule_name)
    _schedule.initialize(
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour,
        slot_duration=slot_duration,
    )
    _dispatcher = Dispatcher(_process_table, _schedule)
    return {
        "ok": True,
        "start_date": _schedule._start_date,
        "end_date": _schedule._end_date,
        "day_count": _schedule.get_day_count(),
    }


def extend_schedule(num_days):
    """Add more days to the end of the schedule. Returns ok/error dict."""
    _schedule, _ = _ensure_schedule()
    if num_days < 1:
        return {"ok": False, "error": "num_days must be >= 1"}
    _schedule.extend(num_days)
    return {"ok": True, "new_end_date": _schedule._end_date, "day_count": _schedule.get_day_count()}


def build_schedule():
    """Run the dispatcher to assign processes to slots. Returns ok dict."""
    _schedule, dispatcher = _ensure_schedule()
    dispatcher.build_schedule()
    return {
        "ok": True,
        "scheduled_count": _schedule.get_scheduled_process_count(),
        "utilization_rate": round(_schedule.get_utilization_rate(), 2),
    }


def get_schedule_view(date):
    """Get one day's schedule as a list of slot entries. Returns dict with ok, date, slots."""
    _schedule, _ = _ensure_schedule()
    day = _schedule.get_day(date)
    if not day:
        return {"ok": False, "error": f"No schedule for date {date}", "slots": []}
    slots = []
    for slot_id, slot in day.get_timeslots().items():
        process = slot.get_process()
        slots.append({
            "slot_id": slot.get_slot_id(),
            "start_time": slot.get_start_time(),
            "end_time": slot.get_end_time(),
            "duration_min": slot.get_duration(),
            "process_id": process.get_id() if process else None,
            "process_name": process.get_name() if process else None,
        })
    return {"ok": True, "date": date, "slots": slots}


def get_schedule_range(start_date, end_date):
    """Get schedule view for a date range. Returns dict with ok, days."""
    _schedule, _ = _ensure_schedule()
    days = _schedule.get_days_range(start_date, end_date)
    result = {}
    for date, day in days.items():
        slots = []
        for slot_id, slot in day.get_timeslots().items():
            process = slot.get_process()
            slots.append({
                "slot_id": slot.get_slot_id(),
                "start_time": slot.get_start_time(),
                "end_time": slot.get_end_time(),
                "process_id": process.get_id() if process else None,
                "process_name": process.get_name() if process else None,
            })
        result[date] = slots
    return {"ok": True, "days": result}


def assign_slot(date, time_or_slot_id, process_id):
    """Assign a process to a slot. time_or_slot_id can be '09:00' or slot_id. Returns ok/error dict."""
    _schedule, _ = _ensure_schedule()
    process = _process_table.get_process(process_id)
    if not process:
        return {"ok": False, "error": f"Process {process_id} not found"}
    slot = _schedule.get_slot(date, time_or_slot_id)
    if not slot:
        return {"ok": False, "error": f"Slot not found for date={date} time={time_or_slot_id}"}
    _schedule.assign_process_to_slot(date, time_or_slot_id, process)
    return {"ok": True, "date": date, "time": slot.get_start_time(), "process_id": process_id}


def clear_slot(date, time_or_slot_id):
    """Clear a slot. Returns ok/error dict."""
    _schedule, _ = _ensure_schedule()
    slot = _schedule.get_slot(date, time_or_slot_id)
    if not slot:
        return {"ok": False, "error": f"Slot not found for date={date} time={time_or_slot_id}"}
    _schedule.clear_slot(date, time_or_slot_id)
    return {"ok": True}


def clear_all_assignments():
    """Clear all slot assignments. Returns ok dict."""
    _schedule, _ = _ensure_schedule()
    _schedule.clear_all_assignments()
    return {"ok": True}


# -----------------------------------------------------------------------------
# Stats / config syscalls
# -----------------------------------------------------------------------------

def get_stats():
    """Get process table and schedule statistics. Returns dict."""
    _schedule, dispatcher = _ensure_schedule()
    next_deadline = _process_table.get_next_deadline()
    return {
        "process_count": _process_table.get_process_count(),
        "process_count_by_status": {
            "new": _process_table.get_process_count("new"),
            "ready": _process_table.get_process_count("ready"),
            "running": _process_table.get_process_count("running"),
            "waiting": _process_table.get_process_count("waiting"),
            "terminated": _process_table.get_process_count("terminated"),
        },
        "total_remaining_time_min": _process_table.get_total_remaining_time(),
        "average_priority": round(_process_table.get_average_priority(), 2),
        "next_deadline": _process_to_dict(next_deadline) if next_deadline else None,
        "schedule_day_count": _schedule.get_day_count(),
        "schedule_total_free_time_min": _schedule.get_total_free_time(),
        "schedule_total_scheduled_time_min": _schedule.get_total_scheduled_time(),
        "schedule_utilization_rate": round(_schedule.get_utilization_rate(), 2),
        "schedule_scheduled_process_count": _schedule.get_scheduled_process_count(),
    }


def set_urgency_function(function_name, weights=None):
    """Set dispatcher urgency function: 'linear', 'exponential', 'logarithmic'. Returns ok/error dict."""
    _schedule, dispatcher = _ensure_schedule()
    try:
        dispatcher.set_urgency_function(function_name, weights=weights)
        return {"ok": True, "urgency_function": function_name}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


def get_next_deadline():
    """Get the process with the nearest upcoming deadline. Returns process dict or None."""
    p = _process_table.get_next_deadline()
    return _process_to_dict(p)


def wake_unblocked_processes():
    """
    Wake any waiting process whose child dependencies have all terminated.
    This is the join() mechanism — call after any process exits.
    Returns dict with ok and list of woken process_ids.
    """
    woken = _process_table.wake_unblocked_processes()
    return {"ok": True, "woken": woken}


def reset_state():
    """Clear all processes and schedule (for testing/examples). Next initialize_schedule or build_schedule will start fresh."""
    global _schedule, _dispatcher
    _process_table.clear_all()
    _schedule = None
    _dispatcher = None
    return {"ok": True}
