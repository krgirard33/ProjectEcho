from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import datetime
from collections import defaultdict
import webbrowser
import threading
import os
# Import the blueprints
from calendar_app import calendar_bp 
from todo import todo_bp 

# Set the app up as a package
app = Flask(__name__)
DB_NAME = 'journal.db'

# --- Database Functions (keep these here or move to a separate config file later) ---
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
            content TEXT NOT NULL
        );
    ''')
    # Add the 'project' column if it doesn't exist
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN project TEXT;")
    except sqlite3.OperationalError:
        # This will fail if the column already exists, which is fine
        pass 

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
    conn.close()

init_db()
# -----------------------------------------------------------------------------------

# Register Blueprints
app.register_blueprint(calendar_bp)
app.register_blueprint(todo_bp)


@app.route('/', methods=('GET', 'POST'))
def index():
    conn = get_db_connection()
    if request.method == 'POST':
        content = request.form['content']
        project = request.form.get('project') or None
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO entries (timestamp, content, project) VALUES (?, ?, ?)',
                     (timestamp, content, project))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    entries = conn.execute('SELECT * FROM entries ORDER BY timestamp ASC').fetchall()
    conn.close()

    entries_by_date = defaultdict(list)
    previous_timestamp = None

    for entry in entries:
        current_timestamp_str = entry['timestamp']
        date_part = current_timestamp_str.split(' ')[0]
        
        # Calculate time difference
        time_elapsed = None
        if previous_timestamp and date_part == previous_timestamp.strftime('%Y-%m-%d'):
            time_elapsed = datetime.datetime.strptime(current_timestamp_str, '%Y-%m-%d %H:%M:%S') - previous_timestamp
            
        # Add the calculated time to the entry dictionary
        entry_with_time = dict(entry)
        entry_with_time['time_elapsed'] = time_elapsed
        
        entries_by_date[date_part].append(entry_with_time)
        previous_timestamp = datetime.datetime.strptime(current_timestamp_str, '%Y-%m-%d %H:%M:%S')
        
    return render_template('index.html', entries_by_date=reversed(entries_by_date.items()))


if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        def open_browser():
            webbrowser.open_new_tab('http://localhost:5000/')

        threading.Timer(1, open_browser).start()
    
    app.run(port=5000, debug=True)