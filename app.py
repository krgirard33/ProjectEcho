from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import datetime
from collections import defaultdict
import webbrowser
import threading
import os

app = Flask(__name__)
DB_NAME = 'journal.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # This allows us to access columns by name
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
    conn.close()

init_db()

@app.route('/', methods=('GET', 'POST'))
def index():
    conn = get_db_connection()
    if request.method == 'POST':
        content = request.form['content']
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO entries (timestamp, content) VALUES (?, ?)',
                     (timestamp, content))
        conn.commit()
        conn.close()
        #SERVER_NAME = 'localhost' 
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

@app.route('/edit/<int:entry_id>', methods=('GET', 'POST'))
def edit(entry_id):
    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    
    if request.method == 'POST':
        content = request.form['content']
        conn.execute('UPDATE entries SET content = ? WHERE id = ?', (content, entry_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    conn.close()
    
    if entry is None:
        return "Entry not found.", 404
        
    return render_template('edit.html', entry=entry)

if __name__ == '__main__':
    # This check ensures the code runs only in the main process
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        def open_browser():
            # Using the default browser is more reliable
            webbrowser.open_new_tab('http://localhost:5000/')

        # We delay opening the browser to give the server a moment to start
        threading.Timer(1, open_browser).start()
    
    app.run(port=5000, debug=True)
    
