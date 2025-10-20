from flask import Blueprint, render_template, request, redirect, url_for
import datetime
import calendar
from collections import defaultdict
import sqlite3
import markdown
from markupsafe import Markup, escape 
from utilities import recalculate_day_durations

# Define the Blueprint. The URL prefix will be '/day' for the view_day route, 
# but the calendar_view route will use its own path.
calendar_bp = Blueprint('calendar_bp', __name__)

# Helper function to get database connection (copied from app.py)
def get_db_connection():
    conn = sqlite3.connect('journal.db')
    conn.row_factory = sqlite3.Row
    return conn

@calendar_bp.route('/calendar', defaults={'year': None, 'month': None})
@calendar_bp.route('/calendar/<int:year>/<int:month>')
def calendar_view(year, month):
    conn = get_db_connection()
    dates_with_entries = conn.execute('SELECT DISTINCT SUBSTR(timestamp, 1, 10) FROM entries').fetchall()
    dates_with_entries = {row[0] for row in dates_with_entries}
    conn.close()
    
    # Determine the month to display
    if year is None or month is None:
        target_date = datetime.date.today()
    else:
        try:
            target_date = datetime.date(year, month, 1)
        except ValueError:
            # Fallback if an invalid date is provided (e.g., month=13)
            target_date = datetime.date.today()
            
    # Calculate previous and next month/year
    first_day_of_month = target_date.replace(day=1)
    
    # Calculate Previous Month
    prev_month_date = first_day_of_month - datetime.timedelta(days=1)
    prev_year = prev_month_date.year
    prev_month = prev_month_date.month
    
    # Calculate Next Month (Add 32 days, then set to the 1st of that month)
    next_month_date = first_day_of_month + datetime.timedelta(days=32)
    next_month_date = next_month_date.replace(day=1)
    next_year = next_month_date.year
    next_month = next_month_date.month

    
    # Generate calendar data for the target month
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    current_month_days = cal.monthdayscalendar(target_date.year, target_date.month)
    month_name = target_date.strftime('%B')
    
    month_data = []
    for week in current_month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                # Use the target month/year for date construction
                current_date = f"{target_date.year:04d}-{target_date.month:02d}-{day:02d}"
                has_entry = current_date in dates_with_entries
                week_data.append({'day': day, 'date': current_date, 'has_entry': has_entry})
        month_data.append(week_data)
        
    return render_template('calendar.html', 
                           month=month_name, 
                           year=target_date.year, 
                           month_data=month_data,
                           
                           # Pass navigation data to the template
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month)

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
    
    # Fetch Journal Entries
    entries = conn.execute('SELECT * FROM entries WHERE SUBSTR(timestamp, 1, 10) = ? ORDER BY timestamp ASC', (date,)).fetchall()
    
    # Fetch Finished To-Do Items
    raw_finished_todos = conn.execute(
        'SELECT * FROM todos WHERE finished_date = ? AND status = "finished" ORDER BY item ASC',
        (date,)
    ).fetchall()

    # Fetch active project names
    project_rows = conn.execute('SELECT name FROM projects WHERE is_active = 1 ORDER BY name ASC').fetchall()
    active_projects = [row['name'] for row in project_rows]

    total_duration_row = conn.execute(
        'SELECT SUM(COALESCE(duration_minutes, 0)) AS total_minutes FROM entries WHERE strftime("%Y-%m-%d", timestamp) = ?',
        (date,)
    ).fetchone() # COALESCE(duration_minutes, 0) treats NULL values as 0

    total_elapsed_minutes = total_duration_row['total_minutes'] if total_duration_row['total_minutes'] is not None else 0

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

    finished_todos = []
    for row in raw_finished_todos:
        todo_item = dict(row) # Convert Row to dictionary
        
        # Convert Markdown to HTML and wrap in Markup
        html_content = markdown.markdown(
            todo_item['item'], 
            extensions=['fenced_code', 'sane_lists']
        )
        if html_content.startswith('<p>') and html_content.endswith('</p>'):
             html_content = html_content[3:-4]
        todo_item['item_html'] = Markup(html_content)
        
        finished_todos.append(todo_item)

    return render_template('day_view.html', 
                           entries=reversed(entries_with_time), 
                           finished_todos=finished_todos, 
                           date=date, 
                           active_projects=active_projects, 
                           total_elapsed_minutes=total_elapsed_minutes)

@calendar_bp.route('/edit/<int:entry_id>', methods=('GET', 'POST'))
def edit(entry_id):
    conn = get_db_connection()
    if request.method == 'POST':
        content = request.form['content']
        project = request.form.get('project') or None
        date_str = request.form['date']
        time_str = request.form['time']
        new_timestamp = f"{date_str} {time_str}:00" 

        conn.execute(
            'UPDATE entries SET content = ?, project = ?, timestamp = ? WHERE id = ?',
            (content, project, new_timestamp, entry_id)
        )
        # After updating, recalculate elapsed times starting from the new timestamp
        recalculate_day_durations(conn, date_str)

        conn.commit()
        conn.close()
        
        # Redirect to the view for the new date
        return redirect(url_for('calendar_bp.view_day', date=date_str))
        
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()

    if entry is None:
        conn.close()
        return "Entry not found.", 404

    # Split the full timestamp for the form inputs
    full_timestamp = entry['timestamp']
    entry_date = full_timestamp.split(' ')[0]   # YYYY-MM-DD
    entry_time = full_timestamp.split(' ')[1][:5] # HH:MM (strips seconds)

    # Fetch active project names
    project_rows = conn.execute('SELECT name FROM projects WHERE is_active = 1 ORDER BY name ASC').fetchall()
    active_projects = [row['name'] for row in project_rows]

    conn.close()
    
    return render_template(
        'edit.html',
        entry=entry,
        entry_date=entry_date, 
        entry_time=entry_time, 
        active_projects=active_projects
    )