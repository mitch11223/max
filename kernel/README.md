# Kernel

Core scheduling logic and data structures.

## Components

- **Process** - Task representation (PCB with deadline, priority, duration)
- **ProcessTable** - Container for all Process objects
- **Schedule** - Calendar structure with Days and TimeSlots
- **Scheduler** - Algorithm that assigns Processes to TimeSlots
- **TimeSlot** - Individual time block within a day
- **Day** - Collection of TimeSlots for a single date

## Data Storage

Currently uses JSON file (`data/processes.json`) for persistence.

## Independence

This module is framework-agnostic - can be used without MCP or OpenClaw.