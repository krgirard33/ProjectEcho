from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import datetime
from collections import defaultdict
import webbrowser
import threading
import os
from markupsafe import Markup, escape
import markdown

# Import the blueprints
from calendar_app import calendar_bp 
from todo import todo_bp 
from projects_bp import projects_bp
from export_data import export_data_bp
from utilities import recalculate_day_durations

# Set the app up as a package
app = Flask(__name__)
DB_NAME = 'journal.db'
app.config['SECRET_KEY'] = 'a-super-secret-key-for-sessions'

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            duration_minutes INTEGER,
            project TEXT
        );
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            item TEXT NOT NULL,
            start_date TEXT,
            due_date TEXT,
            finished_date TEXT,
            priority TEXT NOT NULL,
            status TEXT NOT NULL
        );
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT 1, -- 1 for active, 0 for inactive
            charging_code TEXT NOT NULL
        );
    ''')

    # Add a new column if it doesn't exist
    try:
        conn.execute('''        
        ALTER TABLE projects ADD COLUMN charging_code TEXT;        
        ''')
    except sqlite3.OperationalError:
        # This will fail if the column already exists, which is fine
        pass 

    conn.close()
    
# Jinja Filter for Entry Formatting
def format_entry_content(content):
    # Converts newline characters to <br>, and handles simple markdown for lists.
    if not content:
        return ""

    lines = content.split('\n')
    html_lines = []
    
    in_ul = False
    in_ol = False

    for line in lines:
        stripped_line = line.strip()

        # Unordered List (*)
        if stripped_line.startswith('* '):
            if not in_ul:
                html_lines.append('<ul class="entry-list">')
                in_ul = True
            
            # Close ordered list if transitioning
            if in_ol:
                html_lines.append('</ol>')
                in_ol = False
                
            item_content = stripped_line[2:].strip()
            html_lines.append(f'<li>{escape(item_content)}</li>') 
            continue

        # Ordered List (#)
        elif stripped_line.startswith('# '):
            if not in_ol:
                html_lines.append('<ol class="entry-list">')
                in_ol = True
            
            # Close unordered list if transitioning
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
                
            item_content = stripped_line[2:].strip()
            html_lines.append(f'<li>{escape(item_content)}</li>')
            continue

        # Regular Text (Newlines and Paragraphs)
        else:
            # Close any open list
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            if in_ol:
                html_lines.append('</ol>')
                in_ol = False

            # Convert simple text lines to paragraphs or <br> (for multiline text)
            if stripped_line:
                # Use <p> for blocks of text or simply <br> for line breaks
                escaped_line = escape(line)
                html_lines.append(f'{escaped_line}<br>')
            else:
                # Add an extra <br> for an empty line (paragraph break)
                html_lines.append('<br>')


    # Close any list that might still be open at the end of the entry
    if in_ul:
        html_lines.append('</ul>')
    if in_ol:
        html_lines.append('</ol>')

    # Join lines and return, ensuring we use Markup to tell Jinja it's safe HTML
    return Markup(''.join(html_lines).strip('<br>'))

init_db()
# -----------------------------------------------------------------------------------

# Register Blueprints
app.register_blueprint(calendar_bp)
app.register_blueprint(todo_bp)
app.jinja_env.filters['format_entry'] = format_entry_content
app.register_blueprint(projects_bp)
app.register_blueprint(export_data_bp)


@app.route('/', methods=('GET', 'POST'))
def index():
    conn = get_db_connection()
    if request.method == 'POST':
        content = request.form['content']
        project = request.form.get('project') or None
        now = datetime.datetime.now()
        date_of_entry = now.strftime('%Y-%m-%d')
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO entries (timestamp, content, project) VALUES (?, ?, ?)',
                     (timestamp, content, project))
        # Update elapsed times starting from the new entry's timestamp
        recalculate_day_durations(conn, date_of_entry)

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    # Get active projects for the dropdown
    active_projects = get_active_projects()

    # Get entries from the last 14 days
    fourteen_days_ago = datetime.datetime.now() - datetime.timedelta(days=14)
    cutoff_timestamp = fourteen_days_ago.strftime('%Y-%m-%d %H:%M:%S')
    
    entries = conn.execute(
        'SELECT *, duration_minutes FROM entries WHERE timestamp >= ? ORDER BY timestamp ASC',
        (cutoff_timestamp,)
    ).fetchall()

    entries_by_date = defaultdict(list)
    
    # Group the entries by date
    all_dates = set()
    for entry in entries:
        date_part = entry['timestamp'].split(' ')[0]
        entries_by_date[date_part].append(entry)
        all_dates.add(date_part) # Collect all unique dates

    # Calculate Total Elapsed Time for each unique date
    total_durations_by_date = {} 
    
    for date_str in all_dates:
        # Query the database for the sum of duration_minutes for this date
        total_duration_row = conn.execute(
            'SELECT SUM(COALESCE(duration_minutes, 0)) AS total_minutes FROM entries WHERE strftime("%Y-%m-%d", timestamp) = ?',
            (date_str,)
        ).fetchone()
        
        # Store the minutes
        total_durations_by_date[date_str] = total_duration_row['total_minutes'] if total_duration_row['total_minutes'] is not None else 0

    conn.close()
        
    return render_template('index.html', 
                           entries_by_date=reversed(entries_by_date.items()), 
                           active_projects=active_projects,
                           total_durations=total_durations_by_date
                           )

@app.route('/userguide')
def instructions():
    return render_template('userguide.html')

def get_active_projects():
    conn = get_db_connection()
    # Select only projects marked as active
    projects = conn.execute(
        'SELECT name FROM projects WHERE is_active = 1 ORDER BY name ASC'
    ).fetchall()
    conn.close()
    # Return a list of project names
    return [p['name'] for p in projects]

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        def open_browser():
            webbrowser.open_new_tab('http://localhost:5000/')

        threading.Timer(1, open_browser).start()
    
    app.run(port=5000, debug=True)