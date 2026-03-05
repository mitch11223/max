# Monolithic kernel: all scheduling classes in one module.
# TimeSlot → Day → Process → ProcessTable → Schedule → Dispatcher

from datetime import datetime, timedelta
import json
import math


# -----------------------------------------------------------------------------
# TimeSlot
# -----------------------------------------------------------------------------

class TimeSlot:
    """Represents a single time block that can hold a Process"""
    def __init__(self, start_time, end_time, slot_id):
        self._start_time = start_time
        self._end_time = end_time
        self._assigned_process = None
        self._slot_id = slot_id
        self._duration = self._calculate_duration()

    def get_slot_id(self):
        return self._slot_id

    def _calculate_duration(self):
        """Calculate slot duration in minutes"""
        start_dt = datetime.strptime(self._start_time, "%H:%M")
        end_dt = datetime.strptime(self._end_time, "%H:%M")
        delta = end_dt - start_dt
        return int(delta.total_seconds() / 60)

    def get_duration(self):
        return self._duration

    def get_process(self):
        return self._assigned_process

    def get_start_time(self):
        return self._start_time

    def get_end_time(self):
        return self._end_time

    def assign_process(self, process):
        self._assigned_process = process

    def clear_process(self):
        self._assigned_process = None

    def __repr__(self):
        p = self._assigned_process
        process_name = p.get_name() if p and hasattr(p, "get_name") else (p if p else "Free")
        return f"TimeSlot({self._start_time}-{self._end_time}: {process_name})"


# -----------------------------------------------------------------------------
# Day
# -----------------------------------------------------------------------------

class Day:
    """Represents a single day containing multiple TimeSlots"""

    def __init__(self, date, start_hour, end_hour, slot_duration):
        self._date = date
        self._start_hour = start_hour
        self._end_hour = end_hour
        self._slot_duration = slot_duration
        self._timeslots = {}
        self._generate_timeslots()

    def _generate_timeslots(self):
        """Creates all TimeSlot objects with generated IDs"""
        current_time = datetime.strptime(self._start_hour, "%H:%M")
        end_time = datetime.strptime(self._end_hour, "%H:%M")

        if end_time <= current_time:
            end_time += timedelta(days=1)

        slot_index = 0
        while current_time < end_time:
            next_time = current_time + timedelta(minutes=self._slot_duration)

            slot_id = f"{self._date}_slot_{slot_index}"
            start_str = current_time.strftime("%H:%M")
            end_str = next_time.strftime("%H:%M")

            self._timeslots[slot_id] = TimeSlot(start_str, end_str, slot_id)

            current_time = next_time
            slot_index += 1

    def get_date(self):
        return self._date

    def get_timeslots(self, status=None):
        """Returns timeslots dict filtered by status. status: None (all), "free", or "occupied"""
        if status is None:
            return self._timeslots

        filtered = {}
        for slot_id, slot in self._timeslots.items():
            if status == "free" and slot.get_process() is None:
                filtered[slot_id] = slot
            elif status == "occupied" and slot.get_process() is not None:
                filtered[slot_id] = slot

        return filtered

    def get_slot(self, identifier):
        """Get slot by ID or time (e.g. "2024-03-02_slot_0" or "09:00")"""
        if identifier in self._timeslots:
            return self._timeslots[identifier]

        for slot in self._timeslots.values():
            if slot.get_start_time() == identifier:
                return slot

        return None

    def clear_timeslots(self, identifier=None):
        """Clear timeslots: all if identifier is None, otherwise specific slot"""
        if identifier is None:
            for slot in self._timeslots.values():
                slot.clear_process()
        else:
            slot = self.get_slot(identifier)
            if slot:
                slot.clear_process()

    def get_timeslot_count(self, status=None):
        """Count timeslots by status. status: None (all), "free", or "occupied"""
        return len(self.get_timeslots(status))

    def get_total_free_time(self):
        """Returns total free time in minutes"""
        free_slots = self.get_timeslots(status="free")
        return sum(slot.get_duration() for slot in free_slots.values())

    def __repr__(self):
        total = len(self._timeslots)
        free = self.get_timeslot_count(status="free")
        return f"Day({self._date}, {total} slots, {free} free)"


# -----------------------------------------------------------------------------
# Process
# -----------------------------------------------------------------------------

class Process:
    """Represents a task/process with PCB-like attributes"""

    def __init__(self, name, process_type, process_id, deadline, expected_completion_time,
                 base_priority, preferred_time_windows=None, hard_time_anchor=False,
                 preferred_days=None, repeat_rule=None, outside_peak_multiplier=1.0,
                 peak_multiplier=1.0, repeat_end_date=None, minimum_session_length=1,
                 max_session_length=None, split_across_day=True, tags=None,
                 location=None, dependencies=None):

        self._name = name
        self._type = process_type
        self._id = process_id
        self._deadline = deadline
        self._expected_completion_time = expected_completion_time
        self._remaining_time = expected_completion_time
        self._created_at = datetime.now()
        self._base_priority = base_priority
        self._current_priority = base_priority
        self._aging_counter = 0
        self._preferred_time_windows = preferred_time_windows or []
        self._hard_time_anchor = hard_time_anchor
        self._preferred_days = preferred_days or []
        self._repeat_rule = repeat_rule
        self._repeat_end_date = repeat_end_date
        self._outside_peak_multiplier = outside_peak_multiplier
        self._peak_multiplier = peak_multiplier
        self._minimum_session_length = minimum_session_length
        self._max_session_length = max_session_length
        self._split_across_day = split_across_day
        self._status = "new"
        self._last_scheduled_date = None
        self._total_time_logged = 0
        self._tags = tags or []
        self._location = location
        self._dependencies = dependencies or []

    # Getters
    def get_name(self): return self._name
    def get_type(self): return self._type
    def get_id(self): return self._id
    def get_deadline(self): return self._deadline
    def get_expected_completion_time(self): return self._expected_completion_time
    def get_remaining_time(self): return self._remaining_time
    def get_created_at(self): return self._created_at
    def get_base_priority(self): return self._base_priority
    def get_current_priority(self): return self._current_priority
    def get_aging_counter(self): return self._aging_counter
    def get_preferred_time_windows(self): return self._preferred_time_windows
    def get_hard_time_anchor(self): return self._hard_time_anchor
    def get_preferred_days(self): return self._preferred_days
    def get_repeat_rule(self): return self._repeat_rule
    def get_repeat_end_date(self): return self._repeat_end_date
    def get_outside_peak_multiplier(self): return self._outside_peak_multiplier
    def get_peak_multiplier(self): return self._peak_multiplier
    def get_minimum_session_length(self): return self._minimum_session_length
    def get_max_session_length(self): return self._max_session_length
    def get_split_across_day(self): return self._split_across_day
    def get_status(self): return self._status
    def get_last_scheduled_date(self): return self._last_scheduled_date
    def get_total_time_logged(self): return self._total_time_logged
    def get_tags(self): return self._tags
    def get_location(self): return self._location
    def get_dependencies(self): return self._dependencies

    # Setters
    def set_name(self, name): self._name = name
    def set_deadline(self, deadline): self._deadline = deadline
    def set_expected_completion_time(self, time): self._expected_completion_time = time
    def set_remaining_time(self, time): self._remaining_time = time
    def set_base_priority(self, priority): self._base_priority = priority
    def set_current_priority(self, priority): self._current_priority = priority
    def set_preferred_time_windows(self, windows): self._preferred_time_windows = windows
    def set_hard_time_anchor(self, anchor): self._hard_time_anchor = anchor
    def set_preferred_days(self, days): self._preferred_days = days
    def set_repeat_rule(self, rule): self._repeat_rule = rule
    def set_repeat_end_date(self, date): self._repeat_end_date = date
    def set_outside_peak_multiplier(self, multiplier): self._outside_peak_multiplier = multiplier
    def set_peak_multiplier(self, multiplier): self._peak_multiplier = multiplier
    def set_minimum_session_length(self, length): self._minimum_session_length = length
    def set_max_session_length(self, length): self._max_session_length = length
    def set_split_across_day(self, split): self._split_across_day = split
    def set_last_scheduled_date(self, date): self._last_scheduled_date = date
    def set_tags(self, tags): self._tags = tags
    def set_location(self, location): self._location = location
    def set_dependencies(self, dependencies): self._dependencies = dependencies

    # State transitions
    def admit(self):
        if self._status == "new":
            self._status = "ready"

    def dispatch(self):
        if self._status == "ready":
            self._status = "running"

    def interrupt(self):
        if self._status == "running":
            self._status = "ready"

    def wait(self):
        if self._status == "running":
            self._status = "waiting"

    def wake_up(self):
        if self._status == "waiting":
            self._status = "ready"

    def exit(self):
        if self._status == "running":
            self._status = "terminated"
            self._remaining_time = 0

    # Status checks
    def is_ready(self): return self._status == "ready"
    def is_running(self): return self._status == "running"
    def is_waiting(self): return self._status == "waiting"
    def is_terminated(self): return self._status == "terminated"

    def is_overdue(self):
        if self._deadline:
            return datetime.now() > datetime.strptime(self._deadline, "%Y-%m-%d %H:%M")
        return False

    # Calculators
    def calculate_deadline_urgency(self):
        if not self._deadline:
            return 0
        deadline_dt = datetime.strptime(self._deadline, "%Y-%m-%d %H:%M")
        time_remaining = (deadline_dt - datetime.now()).total_seconds() / 3600
        if time_remaining <= 0:
            return 100
        elif time_remaining <= 24:
            return 50
        elif time_remaining <= 72:
            return 25
        elif time_remaining <= 168:
            return 10
        return 5

    def calculate_current_priority(self):
        urgency = self.calculate_deadline_urgency()
        self._current_priority = self._base_priority + self._aging_counter + urgency
        return self._current_priority

    def increment_aging_counter(self):
        self._aging_counter += 1

    def reset_aging_counter(self):
        self._aging_counter = 0

    def log_time(self, minutes):
        self._total_time_logged += minutes
        self._remaining_time = max(0, self._remaining_time - minutes)

    def get_time_until_deadline(self):
        if not self._deadline:
            return None
        deadline_dt = datetime.strptime(self._deadline, "%Y-%m-%d %H:%M")
        delta = (deadline_dt - datetime.now()).total_seconds() / 60
        return max(0, delta)

    def __repr__(self):
        return (
            f"Process(id={self._id}, name={self._name}, status={self._status}, "
            f"priority={self._current_priority}, remaining={self._remaining_time}min)"
        )


# -----------------------------------------------------------------------------
# ProcessTable
# -----------------------------------------------------------------------------

class ProcessTable:
    """Manages collection of Process objects"""

    def __init__(self):
        self._processes = {}
        self._next_id = 1

    def create_process(self, name, process_type, deadline, expected_completion_time,
                       base_priority, preferred_time_windows=None, hard_time_anchor=False,
                       preferred_days=None, repeat_rule=None, outside_peak_multiplier=1.0,
                       peak_multiplier=1.0, repeat_end_date=None, minimum_session_length=1,
                       max_session_length=None, split_across_day=True, tags=None,
                       location=None, dependencies=None):
        process_id = f"process_{self._next_id}"
        self._next_id += 1
        process = Process(
            name=name, process_type=process_type, process_id=process_id,
            deadline=deadline, expected_completion_time=expected_completion_time,
            base_priority=base_priority, preferred_time_windows=preferred_time_windows,
            hard_time_anchor=hard_time_anchor, preferred_days=preferred_days,
            repeat_rule=repeat_rule, outside_peak_multiplier=outside_peak_multiplier,
            peak_multiplier=peak_multiplier, repeat_end_date=repeat_end_date,
            minimum_session_length=minimum_session_length, max_session_length=max_session_length,
            split_across_day=split_across_day, tags=tags, location=location, dependencies=dependencies
        )
        self._processes[process_id] = process
        return process

    def add_process(self, process):
        self._processes[process.get_id()] = process

    def remove_process(self, process_id):
        if process_id in self._processes:
            del self._processes[process_id]

    def get_process(self, process_id):
        return self._processes.get(process_id)

    def get_all_processes(self):
        return self._processes

    def get_processes_by_status(self, status):
        return {pid: p for pid, p in self._processes.items() if p.get_status() == status}

    def get_processes_by_tag(self, tag):
        return {pid: p for pid, p in self._processes.items() if tag in p.get_tags()}

    def get_ready_processes(self):
        return self.get_processes_by_status("ready")

    def get_overdue_processes(self):
        return {pid: p for pid, p in self._processes.items() if p.is_overdue()}

    def get_processes_by_location(self, location):
        return {pid: p for pid, p in self._processes.items() if p.get_location() == location}

    def get_processes_by_deadline_range(self, start_date, end_date):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M")
        result = {}
        for pid, p in self._processes.items():
            if p.get_deadline():
                deadline_dt = datetime.strptime(p.get_deadline(), "%Y-%m-%d %H:%M")
                if start_dt <= deadline_dt <= end_dt:
                    result[pid] = p
        return result

    def update_all_priorities(self):
        for process in self._processes.values():
            process.calculate_current_priority()

    def increment_all_aging(self):
        for process in self._processes.values():
            if not process.is_terminated():
                process.increment_aging_counter()

    def admit_all_new(self):
        for process in self._processes.values():
            if process.get_status() == "new":
                process.admit()

    def check_dependencies_met(self, process_id):
        process = self.get_process(process_id)
        if not process:
            return False
        for dep_id in process.get_dependencies():
            dep_process = self.get_process(dep_id)
            if not dep_process or not dep_process.is_terminated():
                return False
        return True

    def get_blocked_processes(self):
        return {pid: p for pid, p in self._processes.items()
                if p.is_waiting() and not self.check_dependencies_met(pid)}

    def get_processes_depending_on(self, process_id):
        return {pid: p for pid, p in self._processes.items()
                if process_id in p.get_dependencies()}

    def get_process_count(self, status=None):
        if status is None:
            return len(self._processes)
        return len(self.get_processes_by_status(status))

    def get_total_remaining_time(self):
        return sum(p.get_remaining_time() for p in self._processes.values() if not p.is_terminated())

    def get_average_priority(self):
        if not self._processes:
            return 0
        return sum(p.get_current_priority() for p in self._processes.values()) / len(self._processes)

    def get_next_deadline(self):
        upcoming = []
        now = datetime.now()
        for process in self._processes.values():
            if process.get_deadline() and not process.is_terminated():
                deadline_dt = datetime.strptime(process.get_deadline(), "%Y-%m-%d %H:%M")
                if deadline_dt > now:
                    upcoming.append((deadline_dt, process))
        if not upcoming:
            return None
        upcoming.sort(key=lambda x: x[0])
        return upcoming[0][1]

    def get_stale_processes(self, aging_threshold=10):
        return {pid: p for pid, p in self._processes.items()
                if p.get_aging_counter() >= aging_threshold}

    def wake_unblocked_processes(self):
        """
        Wake any waiting process whose dependencies are now all terminated.
        Call this after a process exits to unblock its dependents (join semantics).
        Returns list of process_ids that were woken.
        """
        woken = []
        for pid, process in self._processes.items():
            if process.is_waiting() and self.check_dependencies_met(pid):
                process.wake_up()
                woken.append(pid)
        return woken

    def save_to_json(self, filepath):
        data = []
        for process in self._processes.values():
            data.append({
                "name": process.get_name(), "type": process.get_type(), "id": process.get_id(),
                "deadline": process.get_deadline(), "expected_completion_time": process.get_expected_completion_time(),
                "remaining_time": process.get_remaining_time(),
                "created_at": process.get_created_at().strftime("%Y-%m-%d %H:%M:%S"),
                "base_priority": process.get_base_priority(), "current_priority": process.get_current_priority(),
                "aging_counter": process.get_aging_counter(),
                "preferred_time_windows": process.get_preferred_time_windows(),
                "hard_time_anchor": process.get_hard_time_anchor(), "preferred_days": process.get_preferred_days(),
                "repeat_rule": process.get_repeat_rule(), "repeat_end_date": process.get_repeat_end_date(),
                "outside_peak_multiplier": process.get_outside_peak_multiplier(),
                "peak_multiplier": process.get_peak_multiplier(),
                "minimum_session_length": process.get_minimum_session_length(),
                "max_session_length": process.get_max_session_length(),
                "split_across_day": process.get_split_across_day(),
                "status": process.get_status(), "last_scheduled_date": process.get_last_scheduled_date(),
                "total_time_logged": process.get_total_time_logged(),
                "tags": process.get_tags(), "location": process.get_location(),
                "dependencies": process.get_dependencies()
            })
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        for process_data in data:
            process = Process(
                name=process_data["name"], process_type=process_data["type"], process_id=process_data["id"],
                deadline=process_data["deadline"], expected_completion_time=process_data["expected_completion_time"],
                base_priority=process_data["base_priority"],
                preferred_time_windows=process_data.get("preferred_time_windows"),
                hard_time_anchor=process_data.get("hard_time_anchor", False),
                preferred_days=process_data.get("preferred_days"), repeat_rule=process_data.get("repeat_rule"),
                outside_peak_multiplier=process_data.get("outside_peak_multiplier", 1.0),
                peak_multiplier=process_data.get("peak_multiplier", 1.0),
                repeat_end_date=process_data.get("repeat_end_date"),
                minimum_session_length=process_data.get("minimum_session_length", 1),
                max_session_length=process_data.get("max_session_length"),
                split_across_day=process_data.get("split_across_day", True),
                tags=process_data.get("tags"), location=process_data.get("location"),
                dependencies=process_data.get("dependencies")
            )
            process._remaining_time = process_data.get("remaining_time")
            process._current_priority = process_data.get("current_priority")
            process._aging_counter = process_data.get("aging_counter", 0)
            process._status = process_data.get("status", "new")
            process._last_scheduled_date = process_data.get("last_scheduled_date")
            process._total_time_logged = process_data.get("total_time_logged", 0)
            self._processes[process.get_id()] = process
            id_num = int(process.get_id().split("_")[1])
            if id_num >= self._next_id:
                self._next_id = id_num + 1

    def clear_all(self):
        self._processes = {}
        self._next_id = 1

    def __repr__(self):
        return f"ProcessTable({len(self._processes)} processes)"


# -----------------------------------------------------------------------------
# Schedule
# -----------------------------------------------------------------------------

class Schedule:
    """Manages a calendar of Days with TimeSlots"""

    def __init__(self, schedule_name="My Schedule"):
        self._schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._schedule_name = schedule_name
        self._days = {}
        self._start_date = None
        self._end_date = None
        self._working_hours = None
        self._slot_duration = None
        self._created_at = datetime.now()
        self._last_updated = datetime.now()

    def initialize(self, start_date=None, end_date=None, start_hour="06:00", end_hour="00:00", slot_duration=60):
        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        self._start_date = start_date
        self._end_date = end_date
        self._working_hours = (start_hour, end_hour)
        self._slot_duration = slot_duration
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            self._days[date_str] = Day(date_str, start_hour, end_hour, slot_duration)
            current_dt += timedelta(days=1)
        self.update_timestamp()

    def refresh(self):
        if self._start_date and self._end_date:
            self.initialize(self._start_date, self._end_date,
                            self._working_hours[0], self._working_hours[1], self._slot_duration)

    def extend(self, num_days):
        if not self._end_date:
            return
        end_dt = datetime.strptime(self._end_date, "%Y-%m-%d")
        new_end_dt = end_dt + timedelta(days=num_days)
        current_dt = end_dt + timedelta(days=1)
        while current_dt <= new_end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            self._days[date_str] = Day(date_str, self._working_hours[0], self._working_hours[1], self._slot_duration)
            current_dt += timedelta(days=1)
        self._end_date = new_end_dt.strftime("%Y-%m-%d")
        self.update_timestamp()

    def get_day(self, date):
        return self._days.get(date)

    def get_all_days(self):
        return self._days

    def get_days_range(self, start_date, end_date):
        return {date: day for date, day in self._days.items() if start_date <= date <= end_date}

    def get_today(self):
        return self.get_day(datetime.now().strftime("%Y-%m-%d"))

    def get_tomorrow(self):
        return self.get_day((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

    def get_next_n_days(self, n):
        result = {}
        for i in range(n):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self._days:
                result[date] = self._days[date]
        return result

    def get_slot(self, date, identifier):
        day = self.get_day(date)
        return day.get_slot(identifier) if day else None

    def get_all_free_slots(self):
        free_slots = {}
        for date, day in self._days.items():
            for slot_id, slot in day.get_timeslots(status="free").items():
                free_slots[f"{date}_{slot_id}"] = slot
        return free_slots

    def get_free_slots_on_date(self, date):
        day = self.get_day(date)
        return day.get_timeslots(status="free") if day else {}

    def find_slot_by_process(self, process_id):
        for date, day in self._days.items():
            for slot_id, slot in day.get_timeslots().items():
                process = slot.get_process()
                if process and process.get_id() == process_id:
                    return (date, slot_id, slot)
        return None

    def get_slots_in_time_window(self, start_time, end_time):
        return {f"{date}_{slot_id}": slot for date, day in self._days.items()
                for slot_id, slot in day.get_timeslots().items()
                if start_time <= slot.get_start_time() <= end_time}

    def assign_process_to_slot(self, date, slot_identifier, process):
        slot = self.get_slot(date, slot_identifier)
        if slot:
            slot.assign_process(process)
            self.update_timestamp()

    def clear_slot(self, date, slot_identifier):
        slot = self.get_slot(date, slot_identifier)
        if slot:
            slot.clear_process()
            self.update_timestamp()

    def clear_all_assignments(self):
        for day in self._days.values():
            day.clear_timeslots()
        self.update_timestamp()

    def clear_day(self, date):
        day = self.get_day(date)
        if day:
            day.clear_timeslots()
            self.update_timestamp()

    def remove_process_from_schedule(self, process_id):
        result = self.find_slot_by_process(process_id)
        if result:
            _, _, slot = result
            slot.clear_process()
            self.update_timestamp()

    def check_conflicts(self):
        conflicts = []
        process_schedule = {}
        for date, day in self._days.items():
            for slot_id, slot in day.get_timeslots().items():
                process = slot.get_process()
                if process:
                    pid = process.get_id()
                    if pid in process_schedule:
                        conflicts.append({"type": "duplicate_process", "process_id": pid,
                                          "locations": [process_schedule[pid], f"{date}_{slot_id}"]})
                    else:
                        process_schedule[pid] = f"{date}_{slot_id}"
        return conflicts

    def has_conflict_at(self, date, time):
        slot = self.get_slot(date, time)
        if not slot or not slot.get_process():
            return False
        pid = slot.get_process().get_id()
        result = self.find_slot_by_process(pid)
        if result:
            found_date, found_slot_id, _ = result
            if found_date != date or found_slot_id != slot.get_slot_id():
                return True
        return False

    def validate_schedule(self):
        return len(self.check_conflicts()) == 0

    def get_total_free_time(self):
        return sum(day.get_total_free_time() for day in self._days.values())

    def get_total_scheduled_time(self):
        total = 0
        for day in self._days.values():
            for slot in day.get_timeslots(status="occupied").values():
                total += slot.get_duration()
        return total

    def get_scheduled_process_count(self):
        process_ids = set()
        for day in self._days.values():
            for slot in day.get_timeslots(status="occupied").values():
                process = slot.get_process()
                if process:
                    process_ids.add(process.get_id())
        return len(process_ids)

    def get_day_count(self):
        return len(self._days)

    def get_utilization_rate(self):
        total_time = self.get_total_free_time() + self.get_total_scheduled_time()
        if total_time == 0:
            return 0
        return (self.get_total_scheduled_time() / total_time) * 100

    def get_daily_breakdown(self):
        breakdown = {}
        for date, day in self._days.items():
            free_time = day.get_total_free_time()
            occupied_slots = day.get_timeslots(status="occupied")
            scheduled_time = sum(slot.get_duration() for slot in occupied_slots.values())
            process_ids = set()
            for slot in occupied_slots.values():
                process = slot.get_process()
                if process:
                    process_ids.add(process.get_id())
            breakdown[date] = {"free_time": free_time, "scheduled_time": scheduled_time, "process_count": len(process_ids)}
        return breakdown

    def print_day(self, date):
        day = self.get_day(date)
        if not day:
            print(f"No schedule for {date}")
            return
        print(f"\n{'='*50}\nSchedule for {date}\n{'='*50}")
        for slot_id, slot in day.get_timeslots().items():
            process = slot.get_process()
            print(f"{slot.get_start_time()}-{slot.get_end_time()}: {process.get_name() if process else 'Free'}")

    def print_full_schedule(self):
        print(f"\n{'#'*50}\nSchedule: {self._schedule_name}\nID: {self._schedule_id}\nPeriod: {self._start_date} to {self._end_date}\n{'#'*50}")
        for date in sorted(self._days.keys()):
            self.print_day(date)

    def export_to_dict(self):
        data = {
            "schedule_id": self._schedule_id, "schedule_name": self._schedule_name,
            "start_date": self._start_date, "end_date": self._end_date,
            "working_hours": self._working_hours, "slot_duration": self._slot_duration,
            "created_at": self._created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated": self._last_updated.strftime("%Y-%m-%d %H:%M:%S"),
            "days": {}
        }
        for date, day in self._days.items():
            day_data = {"date": date, "slots": {}}
            for slot_id, slot in day.get_timeslots().items():
                process = slot.get_process()
                day_data["slots"][slot_id] = {
                    "start_time": slot.get_start_time(), "end_time": slot.get_end_time(),
                    "process_id": process.get_id() if process else None,
                    "process_name": process.get_name() if process else None
                }
            data["days"][date] = day_data
        return data

    def get_schedule_id(self): return self._schedule_id
    def get_schedule_name(self): return self._schedule_name
    def set_schedule_name(self, name): self._schedule_name = name; self.update_timestamp()
    def get_created_at(self): return self._created_at
    def get_last_updated(self): return self._last_updated
    def update_timestamp(self): self._last_updated = datetime.now()

    def __repr__(self):
        return f"Schedule(name='{self._schedule_name}', days={len(self._days)}, period={self._start_date} to {self._end_date})"


# -----------------------------------------------------------------------------
# Dispatcher
# -----------------------------------------------------------------------------

class Dispatcher:
    """Multi-Level Feedback Queue scheduler. Assigns processes to schedule timeslots by priority and urgency."""

    def __init__(self, process_table, schedule, urgency_function="linear", weights=None):
        self._process_table = process_table
        self._schedule = schedule
        self._urgency_function_name = urgency_function
        self._weights = weights or {"deadline": 2.0, "aging": 0.5, "time_remaining": 1.5, "peak": 1.0}
        self._queues = {1: [], 2: [], 3: [], 4: [], 5: []}
        self._urgency_functions = {
            "linear": self._calculate_linear_urgency,
            "exponential": self._calculate_exponential_urgency,
            "logarithmic": self._calculate_logarithmic_urgency
        }

    def _calculate_linear_urgency(self, process):
        deadline_urgency = process.calculate_deadline_urgency()
        aging = process.get_aging_counter()
        time_until_deadline = process.get_time_until_deadline()
        remaining_time = process.get_remaining_time()
        time_pressure = (remaining_time / time_until_deadline * 100) if (time_until_deadline and time_until_deadline > 0) else 100
        return deadline_urgency * self._weights["deadline"] + aging * self._weights["aging"] + time_pressure * self._weights["time_remaining"]

    def _calculate_exponential_urgency(self, process):
        time_until_deadline = process.get_time_until_deadline()
        if not time_until_deadline or time_until_deadline <= 0:
            return 1000
        hours_remaining = time_until_deadline / 60
        deadline_urgency = 100 * math.exp(-hours_remaining / 24)
        aging = process.get_aging_counter()
        remaining_time = process.get_remaining_time()
        return deadline_urgency * self._weights["deadline"] + aging * self._weights["aging"] + (remaining_time / max(hours_remaining, 1)) * self._weights["time_remaining"]

    def _calculate_logarithmic_urgency(self, process):
        time_until_deadline = process.get_time_until_deadline()
        if not time_until_deadline or time_until_deadline <= 0:
            return 1000
        hours_remaining = max(time_until_deadline / 60, 0.1)
        deadline_urgency = 100 - (20 * math.log10(hours_remaining))
        aging = process.get_aging_counter()
        return max(0, deadline_urgency) * self._weights["deadline"] + aging * self._weights["aging"]

    def calculate_urgency(self, process):
        urgency_func = self._urgency_functions.get(self._urgency_function_name)
        if not urgency_func:
            raise ValueError(f"Unknown urgency function: {self._urgency_function_name}")
        return urgency_func(process)

    def assign_to_queue(self, process):
        if process.get_hard_time_anchor():
            return 1
        urgency = self.calculate_urgency(process)
        if urgency >= 80: return 2
        if urgency >= 50: return 3
        if urgency >= 20: return 4
        return 5

    def populate_queues(self):
        for queue in self._queues.values():
            queue.clear()
        for process_id, process in self._process_table.get_ready_processes().items():
            self._queues[self.assign_to_queue(process)].append(process)
        for queue_num in self._queues:
            self._queues[queue_num].sort(key=lambda p: self.calculate_urgency(p), reverse=True)

    def refresh_urgency(self):
        self._process_table.update_all_priorities()
        self.populate_queues()

    def _fits_time_window(self, process, slot):
        preferred_windows = process.get_preferred_time_windows()
        if not preferred_windows:
            return True
        slot_start = slot.get_start_time()
        for window in preferred_windows:
            if isinstance(window, tuple):
                start, end = window
                if start <= slot_start <= end:
                    return True
            elif slot_start == window:
                return True
        return False

    def _check_dependencies_met(self, process):
        return self._process_table.check_dependencies_met(process.get_id())

    def _find_best_slot_for_process(self, process, date=None):
        days_to_search = {date: self._schedule.get_day(date)} if date else self._schedule.get_all_days()
        best_slot = None
        best_score = -1
        min_len = process.get_minimum_session_length()
        if min_len is None:
            min_len = 0
        for day_date, day in days_to_search.items():
            for slot_id, slot in day.get_timeslots(status="free").items():
                if slot.get_duration() < min_len:
                    continue
                score = (50 * self._weights["peak"]) if self._fits_time_window(process, slot) else 0
                score += max(0, 20 - (datetime.strptime(day_date, "%Y-%m-%d") - datetime.now()).days)
                if score > best_score:
                    best_score = score
                    best_slot = (day_date, slot_id, slot)
        return best_slot

    def schedule_hard_anchors(self):
        for process in self._queues[1]:
            for window in (process.get_preferred_time_windows() or []):
                if isinstance(window, str):
                    for date, day in self._schedule.get_all_days().items():
                        slot = day.get_slot(window)
                        if slot and slot.get_process() is None:
                            slot.assign_process(process)
                            process.dispatch()
                            process.reset_aging_counter()
                            break

    def schedule_flexible_tasks(self):
        for queue_num in [2, 3, 4, 5]:
            for process in self._queues[queue_num]:
                if process.is_running():
                    continue
                if not self._check_dependencies_met(process):
                    process.wait()
                    continue
                result = self._find_best_slot_for_process(process)
                if result:
                    date, slot_id, slot = result
                    slot.assign_process(process)
                    process.dispatch()
                    process.reset_aging_counter()
                    process.set_last_scheduled_date(date)

    def distribute_task_across_days(self, process):
        remaining = process.get_remaining_time()
        max_session = process.get_max_session_length()
        if not max_session or remaining <= max_session:
            return
        num_sessions = math.ceil(remaining / max_session)
        scheduled_count = 0
        for date in sorted(self._schedule.get_all_days().keys()):
            if scheduled_count >= num_sessions:
                break
            result = self._find_best_slot_for_process(process, date=date)
            if result:
                _, slot_id, slot = result
                slot.assign_process(process)
                scheduled_count += 1

    def handle_preemption(self, new_process):
        new_urgency = self.calculate_urgency(new_process)
        for date, day in self._schedule.get_all_days().items():
            for slot_id, slot in day.get_timeslots().items():
                current_process = slot.get_process()
                if current_process is None:
                    slot.assign_process(new_process)
                    new_process.dispatch()
                    return True
                if new_urgency > self.calculate_urgency(current_process):
                    slot.clear_process()
                    current_process.interrupt()
                    slot.assign_process(new_process)
                    new_process.dispatch()
                    self._queues[self.assign_to_queue(current_process)].append(current_process)
                    return True
        return False

    def build_schedule(self):
        self._process_table.admit_all_new()
        self.populate_queues()
        self._schedule.clear_all_assignments()
        self.schedule_hard_anchors()
        self.schedule_flexible_tasks()
        for process in self._process_table.get_ready_processes().values():
            if process.get_max_session_length():
                self.distribute_task_across_days(process)
        self._schedule.update_timestamp()

    def set_urgency_function(self, function_name, weights=None):
        if function_name not in self._urgency_functions:
            raise ValueError(f"Unknown function: {function_name}")
        self._urgency_function_name = function_name
        if weights:
            self._weights.update(weights)

    def set_weights(self, weights):
        self._weights.update(weights)

    def get_queue_contents(self):
        return {queue_num: [p.get_name() for p in processes] for queue_num, processes in self._queues.items()}

    def __repr__(self):
        return f"Dispatcher(queued={sum(len(q) for q in self._queues.values())}, function={self._urgency_function_name})"
