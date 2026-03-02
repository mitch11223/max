# Define all the objects that will be used by the Scheduler here

# Process        - akin to a 'Process Control Block' in OS speak
# ProcessTable   - akin to a 'Process Control Block Table' in OS speak
# TimeSlot       - represents a block of time (start, end, assigned process)
# Day            - collection of TimeSlots for a single date
# Schedule       - calendar structure holding multiple Days
# Dispatcher     - the engine that assigns Processes to the CPU(my brain) using TimeSlots