from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
from markupsafe import Markup, escape
import markdown

projects_bp = Blueprint('projects_bp', __name__, url_prefix='/projects')

# Helper function (if not imported)
def get_db_connection():
    # ... (Your existing get_db_connection code) ...
    conn = sqlite3.connect('journal.db') # Use your actual DB path
    conn.row_factory = sqlite3.Row
    return conn

@projects_bp.route('/', methods=('GET', 'POST'))
def manage_projects():
    conn = get_db_connection()
    if request.method == 'POST':
        project_name = request.form['name'].strip()
        
        # Logic to add a new project
        if project_name:
            try:
                conn.execute('INSERT INTO projects (name) VALUES (?)', (project_name,))
                conn.commit()
            except sqlite3.IntegrityError:
                # Handle case where project name is already used (UNIQUE constraint)
                flash(f'Project "{project_name}" already exists.', 'error')
            except Exception as e:
                flash(f'An error occurred: {e}', 'error')
        
        return redirect(url_for('projects_bp.manage_projects'))

    projects = conn.execute('SELECT * FROM projects ORDER BY is_active DESC, name ASC').fetchall()
    conn.close()
    
    return render_template('projects.html', projects=projects)

@projects_bp.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit_project(id):
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name'].strip()
        is_active = 1 if 'is_active' in request.form else 0
        
        if name:
            try:
                conn.execute('UPDATE projects SET name = ?, is_active = ? WHERE id = ?', (name, is_active, id))
                conn.commit()
            except sqlite3.IntegrityError:
                flash(f'Project name "{name}" is already in use.', 'error')
            except Exception as e:
                flash(f'An error occurred: {e}', 'error')
        
        conn.close()
        return redirect(url_for('projects_bp.manage_projects'))
    
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if project is None:
        return "Project not found", 404
        
    return render_template('edit_project.html', project=project)

@projects_bp.route('/dashboard/<project_name>')
def project_dashboard(project_name):
    conn = get_db_connection()

    # Fetch Journal Entries for the Project
    journal_entries = conn.execute(
        'SELECT * FROM entries WHERE project = ? ORDER BY timestamp DESC',
        (project_name,)
    ).fetchall()
    
    # Fetch To-Do Items (Active and Finished)
    all_todos = conn.execute(
        'SELECT * FROM todos WHERE project = ? ORDER BY status, due_date ASC',
        (project_name,)
    ).fetchall()
    
    conn.close()

    # Data Processing and Markdown Conversion 
    active_todos = []
    finished_todos = []
    
    # Loop through raw rows to apply Markdown and classify by status
    for row in all_todos:
        todo_item = dict(row) 
        
        # Convert Markdown to HTML and wrap in Markup for safe rendering
        html_content = markdown.markdown(todo_item['item'])
        todo_item['item_html'] = Markup(html_content)
        
        # Classify for metrics and template
        if todo_item['status'] != 'finished':
            active_todos.append(todo_item)
        else:
            finished_todos.append(todo_item)

    # Metrics Calculation
    total_tasks = len(all_todos)
    finished_count = len(finished_todos)
    
    # Calculate simple completion percentage
    completion_percentage = (finished_count / total_tasks * 100) if total_tasks > 0 else 0
    
    # Data Filtering for Template 
    return render_template(
        'project_dashboard.html',
        project_name=project_name,
        entries=journal_entries,
        active_todos=active_todos,
        finished_todos=finished_todos,
        total_tasks=total_tasks,
        completion_percentage=round(completion_percentage, 1)
    )