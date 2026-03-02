# sample_usage.py
# Complete example setup and interactive testing

from datetime import datetime, timedelta
from kernel import Process, ProcessTable, Schedule, Day, TimeSlot

def setup_sample_data():
    """Create sample processes and schedule"""
    
    print("="*60)
    print("SETTING UP SAMPLE DATA")
    print("="*60)
    
    # Create ProcessTable
    print("\n1. Creating ProcessTable...")
    pt = ProcessTable()
    
    # Create sample processes
    print("\n2. Creating sample processes...")
    
    # Process 1: Gym (recurring, hard time anchor)
    gym = pt.create_process(
        name="Morning Gym",
        process_type="recurring",
        deadline=None,
        expected_completion_time=60,
        base_priority=3,
        preferred_time_windows=["06:00-08:00"],
        hard_time_anchor=True,
        repeat_rule="daily",
        tags=["health", "routine"],
        location="gym"
    )
    print(f"   Created: {gym}")
    
    # Process 2: COSC Assignment (deadline-driven)
    tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d 23:59")
    cosc = pt.create_process(
        name="COSC 3P71 Assignment",
        process_type="one-time",
        deadline=tomorrow,
        expected_completion_time=180,  # 3 hours
        base_priority=5,
        minimum_session_length=2,  # At least 2 slots
        max_session_length=3,
        tags=["academic", "urgent"],
        location="library"
    )
    print(f"   Created: {cosc}")
    
    # Process 3: Portfolio work (flexible)
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d 17:00")
    portfolio = pt.create_process(
        name="Portfolio Website",
        process_type="one-time",
        deadline=next_week,
        expected_completion_time=120,
        base_priority=3,
        split_across_day=True,
        tags=["career", "personal"],
        location="home"
    )
    print(f"   Created: {portfolio}")
    
    # Process 4: Lunch (recurring, preferred time)
    lunch = pt.create_process(
        name="Lunch Break",
        process_type="recurring",
        deadline=None,
        expected_completion_time=30,
        base_priority=2,
        preferred_time_windows=["12:00-13:00"],
        repeat_rule="daily",
        tags=["routine", "health"],
        location="home"
    )
    print(f"   Created: {lunch}")
    
    # Process 5: Evening study
    study = pt.create_process(
        name="Study Session",
        process_type="recurring",
        deadline=None,
        expected_completion_time=90,
        base_priority=4,
        preferred_time_windows=["19:00-22:00"],
        tags=["academic"],
        location="library"
    )
    print(f"   Created: {study}")
    
    # Admit all processes to ready state
    print("\n3. Admitting all processes to 'ready' state...")
    pt.admit_all_new()
    
    # Create Schedule
    print("\n4. Creating Schedule (7 days, 6am-midnight, 60min slots)...")
    schedule = Schedule(schedule_name="My Weekly Schedule")
    schedule.initialize()  # Uses defaults
    
    print(f"   {schedule}")
    print(f"   Total slots: {sum(day.get_timeslot_count() for day in schedule.get_all_days().values())}")
    print(f"   Total free time: {schedule.get_total_free_time()} minutes")
    
    return pt, schedule


def manual_schedule_demo(pt, schedule):
    """Manually assign some processes to demonstrate"""
    
    print("\n" + "="*60)
    print("MANUAL SCHEDULING DEMO")
    print("="*60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get processes
    gym = pt.get_process("process_1")
    cosc = pt.get_process("process_2")
    lunch = pt.get_process("process_3")
    
    print(f"\n1. Assigning '{gym.get_name()}' to today at 06:00...")
    schedule.assign_process_to_slot(today, "06:00", gym)
    
    print(f"2. Assigning '{cosc.get_name()}' to today at 09:00...")
    schedule.assign_process_to_slot(today, "09:00", cosc)
    
    print(f"3. Assigning '{lunch.get_name()}' to today at 12:00...")
    schedule.assign_process_to_slot(today, "12:00", lunch)
    
    print("\n" + "-"*60)
    print("TODAY'S SCHEDULE:")
    print("-"*60)
    schedule.print_day(today)
    
    print(f"\nSchedule utilization: {schedule.get_utilization_rate():.2f}%")
    print(f"Processes scheduled: {schedule.get_scheduled_process_count()}")


def show_stats(pt, schedule):
    """Display statistics"""
    
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    
    print("\nProcessTable Stats:")
    print(f"  Total processes: {pt.get_process_count()}")
    print(f"  Ready processes: {pt.get_process_count(status='ready')}")
    print(f"  Running processes: {pt.get_process_count(status='running')}")
    print(f"  Total remaining time: {pt.get_total_remaining_time()} minutes")
    print(f"  Average priority: {pt.get_average_priority():.2f}")
    
    next_deadline = pt.get_next_deadline()
    if next_deadline:
        print(f"  Next deadline: {next_deadline.get_name()} at {next_deadline.get_deadline()}")
    
    print("\nSchedule Stats:")
    print(f"  Total days: {schedule.get_day_count()}")
    print(f"  Total free time: {schedule.get_total_free_time()} minutes")
    print(f"  Total scheduled time: {schedule.get_total_scheduled_time()} minutes")
    print(f"  Utilization rate: {schedule.get_utilization_rate():.2f}%")
    print(f"  Unique processes scheduled: {schedule.get_scheduled_process_count()}")


def interactive_loop(pt, schedule):
    """Interactive testing loop"""
    
    print("\n" + "="*60)
    print("INTERACTIVE MODE")
    print("="*60)
    print("\nCommands:")
    print("  1 - Create new process")
    print("  2 - List all processes")
    print("  3 - Assign process to slot")
    print("  4 - View day schedule")
    print("  5 - View schedule stats")
    print("  6 - Clear all assignments")
    print("  7 - Update process priority")
    print("  8 - Save processes to JSON")
    print("  9 - Load processes from JSON")
    print("  0 - Exit")
    
    while True:
        print("\n" + "-"*60)
        choice = input("Enter command: ").strip()
        
        if choice == "0":
            print("Exiting...")
            break
        
        elif choice == "1":
            # Create process
            print("\n--- Create New Process ---")
            name = input("Name: ")
            ptype = input("Type (one-time/recurring): ") or "one-time"
            deadline_str = input("Deadline (YYYY-MM-DD HH:MM) or leave blank: ").strip()
            deadline = deadline_str if deadline_str else None
            duration = int(input("Expected duration (minutes): ") or 60)
            priority = int(input("Base priority (1-5): ") or 3)
            tags_str = input("Tags (comma-separated): ").strip()
            tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
            
            process = pt.create_process(
                name=name,
                process_type=ptype,
                deadline=deadline,
                expected_completion_time=duration,
                base_priority=priority,
                tags=tags
            )
            process.admit()
            print(f"Created: {process}")
        
        elif choice == "2":
            # List processes
            print("\n--- All Processes ---")
            for pid, process in pt.get_all_processes().items():
                print(f"{pid}: {process}")
        
        elif choice == "3":
            # Assign process to slot
            print("\n--- Assign Process ---")
            date = input("Date (YYYY-MM-DD) or 'today': ").strip()
            if date == "today":
                date = datetime.now().strftime("%Y-%m-%d")
            
            time = input("Time (HH:MM): ").strip()
            pid = input("Process ID: ").strip()
            
            process = pt.get_process(pid)
            if process:
                schedule.assign_process_to_slot(date, time, process)
                print(f"Assigned {process.get_name()} to {date} at {time}")
            else:
                print("Process not found!")
        
        elif choice == "4":
            # View day
            print("\n--- View Day Schedule ---")
            date = input("Date (YYYY-MM-DD) or 'today': ").strip()
            if date == "today":
                date = datetime.now().strftime("%Y-%m-%d")
            
            schedule.print_day(date)
        
        elif choice == "5":
            # Stats
            show_stats(pt, schedule)
        
        elif choice == "6":
            # Clear assignments
            confirm = input("Clear all assignments? (yes/no): ").strip().lower()
            if confirm == "yes":
                schedule.clear_all_assignments()
                print("All assignments cleared!")
        
        elif choice == "7":
            # Update priority
            print("\n--- Update Process Priority ---")
            pid = input("Process ID: ").strip()
            process = pt.get_process(pid)
            if process:
                print(f"Current priority: {process.get_current_priority()}")
                process.calculate_current_priority()
                print(f"Recalculated priority: {process.get_current_priority()}")
            else:
                print("Process not found!")
        
        elif choice == "8":
            # Save to JSON
            filepath = input("Filepath (default: processes.json): ").strip() or "processes.json"
            pt.save_to_json(filepath)
            print(f"Saved to {filepath}")
        
        elif choice == "9":
            # Load from JSON
            filepath = input("Filepath (default: processes.json): ").strip() or "processes.json"
            pt.load_from_json(filepath)
            print(f"Loaded from {filepath}")
        
        else:
            print("Invalid command!")


def main():
    """Main entry point"""
    
    # Setup
    pt, schedule = setup_sample_data()
    
    # Demo manual scheduling
    manual_schedule_demo(pt, schedule)
    
    # Show stats
    show_stats(pt, schedule)
    
    # Interactive mode
    interactive_loop(pt, schedule)


if __name__ == "__main__":
    main()