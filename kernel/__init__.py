# Kernel: implementation (kernel.py) + syscalls (syscalls.py).
# External code should use kernel.syscalls only; kernel.kernel is internal.

from .kernel import (
    TimeSlot,
    Day,
    Process,
    ProcessTable,
    Schedule,
    Dispatcher,
)

# Re-export syscalls as the public surface (optional: from kernel import syscalls)
from . import syscalls

__all__ = [
    "TimeSlot",
    "Day",
    "Process",
    "ProcessTable",
    "Schedule",
    "Dispatcher",
    "syscalls",
]
