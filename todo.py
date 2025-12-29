from flask import Blueprint, render_template, request, redirect, url_for, flash
from collections import defaultdict
import sqlite3
import datetime
import markdown
from markupsafe import Markup, escape 
from utilities import run_daily_recurrence_check, calculate_next_due_date 

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
        
        # When adding a manual todo, recurring_id is NULL
        conn.execute('INSERT INTO todos (project, item, start_date, due_date, finished_date, priority, status, recurring_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (project, item, start_date, due_date, finished_date, priority, status, None))
        conn.commit()


    # Fetch all active projects for the dropdown
    project_rows = conn.execute('SELECT name FROM projects WHERE is_active = 1 ORDER BY name ASC').fetchall()
    active_projects = [row['name'] for row in project_rows]

        
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
        todo_item = dict(todo_item)
        html_content = markdown.markdown(todo_item['item'])
        todo_item['item_html'] = Markup(html_content)
        active_todos_by_project[todo_item['project']].append(todo_item)
    
    # Process Recent Finished Todos
    for todo_item in finished_todos_recent:
        todo_item = dict(todo_item)
        html_content = markdown.markdown(todo_item['item'])
        todo_item['item_html'] = Markup(html_content)
        finished_todos_by_project[todo_item['project']].append(todo_item)

    sorted_finished_projects = sorted(finished_todos_by_project.items())
    
    # The redirect should handle the POST request
    if request.method == 'POST':
        return redirect(url_for('todo_bp.todo'))
        
    return render_template('todo.html', 
                           active_todos_by_project=active_todos_by_project, 
                           finished_todos_by_project=sorted_finished_projects,
                           active_projects=active_projects
                           )  
        
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
        submitted_finished_date = request.form['finished_date'] or None # <--- NEW LINE
        
        # Determine the finished_date based on the new status
        current_data = conn.execute('SELECT finished_date, recurring_id FROM todos WHERE id = ?', (item_id,)).fetchone()
        
        current_finished_date = current_data['finished_date'] if current_data else None
        recurring_template_id = current_data['recurring_id'] if current_data else None
        
        is_being_finished = False
        final_finished_date = None 
        
        # Handle manual date input
        if status == 'finished':
            # Use the submitted date if available, otherwise default to today
            final_finished_date = submitted_finished_date or datetime.date.today().strftime('%Y-%m-%d')
            
            # Check if this transition triggers recurrence
            if not current_finished_date:
                is_being_finished = True 

        elif status != 'finished':
            # Status is not finished, so finished_date must be NULL
            final_finished_date = None
            
        # Update the current task using the determined final_finished_date
        conn.execute('''
            UPDATE todos 
            SET project = ?, item = ?, start_date = ?, due_date = ?, finished_date = ?, priority = ?, status = ? 
            WHERE id = ?
        ''', (project, item, start_date, due_date, final_finished_date, priority, status, item_id)) 
        
        # Check for recurrance & create new todo
        if is_being_finished and recurring_template_id:
            # Get the template details
            template = conn.execute('SELECT * FROM recurring_todos WHERE id = ?', (recurring_template_id,)).fetchone()
            
            if template and template['is_active']:
                from utilities import calculate_next_due_date
                
                # Use the DUE DATE of the just finished todo as the basis for the next calculation
                next_due_date_str = calculate_next_due_date(due_date, template['recurrence_type']) 
                
                # Insert the new todo instance
                conn.execute(
                    'INSERT INTO todos (item, project, due_date, priority, status, recurring_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (template['item'], template['project'], next_due_date_str, priority, 'active', recurring_template_id)
                )

                # Update the recurring template's next_due_date
                conn.execute(
                    'UPDATE recurring_todos SET next_due_date = ? WHERE id = ?',
                    (next_due_date_str, recurring_template_id)
                )
                flash(f"Next instance of recurring task '{template['item']}' created for {next_due_date_str}!", 'success')
                
        conn.commit()
        conn.close()
        return redirect(url_for('todo_bp.todo'))
        
    # Fetch active project names 
    project_rows = conn.execute('SELECT name FROM projects WHERE is_active = 1 ORDER BY name ASC').fetchall()
    active_projects = [row['name'] for row in project_rows]

    # Fetch specific todo
    todo_item = conn.execute('SELECT * FROM todos WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    if todo_item is None:
        return "Todo item not found.", 404
        
    return render_template('edit_todo.html', item=todo_item, active_projects=active_projects)

@todo_bp.route('/check_recurring', methods=['POST'])
def trigger_recurring_check():
    tasks_created = run_daily_recurrence_check()
    
    if tasks_created > 0:
        flash(f'Daily recurrence check complete: {tasks_created} new task(s) created!', 'success')
    else:
        flash('Daily recurrence check complete: No new tasks were due today.', 'info')
    
    return redirect(url_for('todo_bp.todo'))