from flask import Blueprint, render_template, request, redirect, url_for
from collections import defaultdict
import sqlite3
import datetime

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

        # Check if the task is being marked as finished and set the finished_date
        finished_date = datetime.date.today().strftime('%Y-%m-%d') if status == 'finished' else None
        
        conn.execute('INSERT INTO todos (project, item, start_date, due_date, finished_date, priority, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (project, item, start_date, due_date, finished_date, priority, status))
        conn.commit()
        
    # Calculate the cutoff date (31 days ago)
    thirty_one_days_ago = datetime.date.today() - datetime.timedelta(days=31)
    cutoff_date = thirty_one_days_ago.strftime('%Y-%m-%d')

    # Query Active Todos
    # Fetch all todos that are NOT finished
    active_todos = conn.execute(
        'SELECT * FROM todos WHERE status != "finished" ORDER BY project, due_date ASC'
    ).fetchall()

    # Query Finished Todos (Filtered by Date)
    # Fetch all finished todos where the finished_date is ON OR AFTER the cutoff date
    finished_todos_recent = conn.execute(
        'SELECT * FROM todos WHERE status = "finished" AND finished_date >= ? ORDER BY project, finished_date DESC',
        (cutoff_date,)
    ).fetchall()

    conn.close()

    active_todos_by_project = defaultdict(list)
    finished_todos_by_project = defaultdict(list)
    
    # Process Active Todos
    for todo_item in active_todos:
        active_todos_by_project[todo_item['project']].append(todo_item)
    
    # Process Recent Finished Todos
    for todo_item in finished_todos_recent:
        finished_todos_by_project[todo_item['project']].append(todo_item)

    sorted_finished_projects = sorted(finished_todos_by_project.items())
    
    # NOTE: The redirect should handle the POST request
    if request.method == 'POST':
        return redirect(url_for('todo_bp.todo'))
        
    return render_template('todo.html', 
                           active_todos_by_project=active_todos_by_project, 
                           finished_todos_by_project=sorted_finished_projects)  
        
# Editing Todos
@todo_bp.route('/edit/<int:item_id>', methods=('GET', 'POST'))
def edit_todo(item_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        project = request.form['project']
        item = request.form['item']
        start_date = request.form['start_date'] or None
        due_date = request.form['due_date'] or None
        priority = request.form['priority']
        status = request.form['status']
        
        # Determine the finished_date based on the new status
        # ... (Your finished_date logic is correct here)
        current_finished_date_tuple = conn.execute('SELECT finished_date FROM todos WHERE id = ?', (item_id,)).fetchone()
        current_finished_date = current_finished_date_tuple[0] if current_finished_date_tuple else None
        
        if status == 'finished' and not current_finished_date:
            finished_date = datetime.date.today().strftime('%Y-%m-%d')
        elif status != 'finished' and current_finished_date:
            finished_date = None
        else:
            finished_date = current_finished_date

        conn.execute('''
            UPDATE todos 
            SET project = ?, item = ?, start_date = ?, due_date = ?, finished_date = ?, priority = ?, status = ? 
            WHERE id = ?
        ''', (project, item, start_date, due_date, finished_date, priority, status, item_id))
        conn.commit()
        conn.close()
        return redirect(url_for('todo_bp.todo'))
        
    todo_item = conn.execute('SELECT * FROM todos WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    if todo_item is None:
        return "Todo item not found.", 404
        
    return render_template('edit_todo.html', item=todo_item)
