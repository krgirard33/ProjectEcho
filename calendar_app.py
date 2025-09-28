from flask import Blueprint, render_template, request, redirect, url_for
import datetime
import calendar
from collections import defaultdict
import sqlite3

# Define the Blueprint. The URL prefix will be '/day' for the view_day route, 
# but the calendar_view route will use its own path.
calendar_bp = Blueprint('calendar_bp', __name__)

# Helper function to get database connection (copied from app.py)
def get_db_connection():
    conn = sqlite3.connect('journal.db')
    conn.row_factory = sqlite3.Row
    return conn

@calendar_bp.route('/calendar')
def calendar_view():
    conn = get_db_connection()
    dates_with_entries = conn.execute('SELECT DISTINCT SUBSTR(timestamp, 1, 10) FROM entries').fetchall()
    dates_with_entries = {row[0] for row in dates_with_entries}
    conn.close()
    
    today = datetime.date.today()
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    current_month_days = cal.monthdayscalendar(today.year, today.month)
    month_name = today.strftime('%B')
    
    month_data = []
    for week in current_month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                current_date = f"{today.year:04d}-{today.month:02d}-{day:02d}"
                has_entry = current_date in dates_with_entries
                week_data.append({'day': day, 'date': current_date, 'has_entry': has_entry})
        month_data.append(week_data)
        
    # Note: url_for in the template will now need to use 'calendar_bp.view_day'
    return render_template('calendar.html', month=month_name, year=today.year, month_data=month_data)

@calendar_bp.route('/day/<date>', methods=('GET', 'POST'))
def view_day(date):
    conn = get_db_connection()
    if request.method == 'POST':
        content = request.form['content']
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO entries (timestamp, content) VALUES (?, ?)',
                     (timestamp, content))
        conn.commit()
        conn.close()
        return redirect(url_for('calendar_bp.view_day', date=date))
    
    entries = conn.execute('SELECT * FROM entries WHERE SUBSTR(timestamp, 1, 10) = ? ORDER BY timestamp ASC', (date,)).fetchall()
    conn.close()

    entries_with_time = []
    previous_timestamp = None
    
    for entry in entries:
        current_timestamp_str = entry['timestamp']
        
        time_elapsed = None
        if previous_timestamp:
            time_elapsed = datetime.datetime.strptime(current_timestamp_str, '%Y-%m-%d %H:%M:%S') - previous_timestamp
            
        entry_with_time = dict(entry)
        entry_with_time['time_elapsed'] = time_elapsed
        
        entries_with_time.append(entry_with_time)
        previous_timestamp = datetime.datetime.strptime(current_timestamp_str, '%Y-%m-%d %H:%M:%S')

    entries_with_time.reverse()

    return render_template('day_view.html', entries=entries_with_time, date=date)

@calendar_bp.route('/edit/<int:entry_id>', methods=('GET', 'POST'))
def edit(entry_id):
    conn = get_db_connection()
    if request.method == 'POST':
        content = request.form['content']
        original_date = request.form['original_date']
        conn.execute('UPDATE entries SET content = ? WHERE id = ?', (content, entry_id))
        conn.commit()
        conn.close()
        return redirect(url_for('calendar_bp.view_day', date=original_date))
        
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    conn.close()
    
    if entry is None:
        return "Entry not found.", 404
    
    original_date = entry['timestamp'].split(' ')[0]
    return render_template('edit.html', entry=entry, original_date=original_date)