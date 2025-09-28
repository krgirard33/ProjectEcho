from flask import Blueprint, render_template, request, redirect, url_for
from collections import defaultdict
import sqlite3

# Define the Blueprint. The URL prefix will be '/todo'
todo_bp = Blueprint('todo_bp', __name__, url_prefix='/todo')

# Helper function to get database connection (copied from app.py)
def get_db_connection():
    conn = sqlite3.connect('journal.db')
    conn.row_factory = sqlite3.Row
    return conn

@todo_bp.route('/', methods=('GET', 'POST'))
def todo():
    conn = get_db_connection()
    if request.method == 'POST':
        project = request.form['project']
        item = request.form['item']
        start_date = request.form['start_date'] or None
        due_date = request.form['due_date'] or None
        priority = request.form['priority']
        status = request.form['status']
        
        conn.execute('INSERT INTO todos (project, item, start_date, due_date, priority, status) VALUES (?, ?, ?, ?, ?, ?)',
                     (project, item, start_date, due_date, priority, status))
        conn.commit()
        conn.close()
        return redirect(url_for('todo_bp.todo'))
        
    todos = conn.execute('SELECT * FROM todos ORDER BY project, due_date ASC').fetchall()
    conn.close()
    
    todos_by_project = defaultdict(list)
    for todo_item in todos:
        todos_by_project[todo_item['project']].append(todo_item)
        
    return render_template('todo.html', todos_by_project=todos_by_project)