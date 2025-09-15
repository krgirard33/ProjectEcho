from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import datetime
from collections import defaultdict

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
        return redirect(url_for('index'))
    
    entries = conn.execute('SELECT * FROM entries ORDER BY timestamp DESC').fetchall()
    conn.close()

    # Create a dictionary to group entries by date
    entries_by_date = defaultdict(list)
    for entry in entries:
        date_part = entry['timestamp'].split(' ')[0] # Extract YYYY-MM-DD
        entries_by_date[date_part].append(entry)

    return render_template('index.html', entries_by_date=entries_by_date)

if __name__ == '__main__':
    app.run(debug=True)

    """
    import os
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
    """
