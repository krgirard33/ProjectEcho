import datetime

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