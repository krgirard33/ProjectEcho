import datetime
import sqlite3

def get_db_connection():
    conn = sqlite3.connect("journal.db")
    conn.row_factory = sqlite3.Row
    return conn

def recalculate_day_durations(conn, date_str):
    """
    Calculates the time elapsed since the PREVIOUS entry on the given day (date_str).
    The elapsed duration is stored on the current entry.
    """
    # Fetch all entries for the given date, ordered chronologically
    entries_for_day = conn.execute(
        'SELECT id, timestamp FROM entries WHERE strftime("%Y-%m-%d", timestamp) = ? ORDER BY timestamp ASC',
        (date_str,)
    ).fetchall()

    if not entries_for_day:
        return

    # List of entry IDs and their timestamps
    entry_data = []
    for entry in entries_for_day:
        entry_data.append({
            'id': entry['id'],
            'timestamp_dt': datetime.datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
        })

    # Iterate through the entries to calculate duration since the PREVIOUS entry
    for i in range(len(entry_data)):
        current_entry = entry_data[i]
        
        if i == 0:
            # The first entry of the day has no preceding entry
            duration_minutes = None
        else:
            # The duration is the time difference from the previous entry
            previous_entry = entry_data[i-1]
            time_difference = current_entry['timestamp_dt'] - previous_entry['timestamp_dt']
            duration_minutes = int(time_difference.total_seconds() / 60)
        
        # Update the database: The calculated duration is applied to the current entry's ID
        conn.execute(
            'UPDATE entries SET duration_minutes = ? WHERE id = ?',
            (duration_minutes, current_entry['id'])
        )

        conn.commit()

def calculate_next_due_date(current_date_str, recurrence_type):
    current_date = datetime.datetime.strptime(current_date_str, '%Y-%m-%d')
    
    if recurrence_type == 'daily':
        next_date = current_date + datetime.timedelta(days=1)
    elif recurrence_type == 'weekly':
        next_date = current_date + datetime.timedelta(weeks=1)
    elif recurrence_type == 'monthly':
        # Simple monthly increment: adds 30 days, slightly inaccurate but common for simple tracking
        next_date = current_date + datetime.timedelta(days=30) 
        # For precise monthly increment, you would use a library or more complex datetime logic.
    else:
        return None
        
    return next_date.strftime('%Y-%m-%d')

def run_daily_recurrence_check():
    conn = get_db_connection()
    today_date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Fetch active templates where next_due_date is today or in the past
    templates_to_process = conn.execute(
        'SELECT * FROM recurring_todos WHERE is_active = 1 AND next_due_date <= ?',
        (today_date_str,)
    ).fetchall()
    
    new_tasks_created = 0
    
    for template in templates_to_process:
        default_priority = 'low'

        # Create a new To-Do entry
        conn.execute(
            'INSERT INTO todos (item, project, status, start_date, priority) VALUES (?, ?, ?, ?, ?)',
            (template['item'], template['project'], 'active', today_date_str, default_priority)
        )
        new_tasks_created += 1
        
        # Calculate and update the next due date for the template
        new_next_due_date = calculate_next_due_date(today_date_str, template['recurrence_type'])
        
        conn.execute(
            'UPDATE recurring_todos SET next_due_date = ? WHERE id = ?',
            (new_next_due_date, template['id'])
        )
        
    conn.commit()
    conn.close()
    print(f"Daily check complete. Created {new_tasks_created} new tasks.")
    return new_tasks_created

def check_time():
    # Get the current time
    current_time = datetime.datetime.now().time()
    
    # Define the target time (8:00 AM)
    target_time = datetime.time(hour=8, minute=0)
    
    # The comparison works directly on time objects
    if current_time >= target_time:
        run_daily_recurrence_check()
        print(f"Current time ({current_time.strftime('%H:%M')}) is after 8:00 AM. Doing the thing!")
        return True

    else:
        print(f"Current time ({current_time.strftime('%H:%M')}) is before 8:00 AM. Skipping.")
        return False