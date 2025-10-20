from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
from markupsafe import Markup, escape
import markdown
from collections import defaultdict

projects_bp = Blueprint('projects_bp', __name__, url_prefix='/projects')

# Helper function 
def get_db_connection():
    conn = sqlite3.connect('journal.db') # Use your actual DB path
    conn.row_factory = sqlite3.Row
    return conn

@projects_bp.route('/', methods=('GET', 'POST'))
def projects():
    conn = get_db_connection()
    if request.method == 'POST':
        project_name = request.form['name'].strip()
        charging_code = request.form.get('charging_code', '').strip() or None
        status = request.form.get('status', 'active')
        is_active = 1 if status == 'active' else 0
        
        # Logic to add a new project
        if project_name:
            try:
                conn.execute('INSERT INTO projects (name, status, is_active, charging_code) VALUES (?, ?, ?, ?)', 
                    (project_name, status, is_active, charging_code))
                conn.commit()
            except sqlite3.IntegrityError:
                # Handle case where project name is already used (UNIQUE constraint)
                flash(f'Project "{project_name}" already exists.', 'error')
            except Exception as e:
                flash(f'An error occurred: {e}', 'error')
        
        return redirect(url_for('projects_bp.projects'))

    projects = conn.execute('SELECT * FROM projects ORDER BY is_active DESC, name ASC').fetchall()
    conn.close()
    
    return render_template('projects.html', projects=projects)

@projects_bp.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit_project(id):
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name'].strip()
        charging_code = request.form.get('charging_code', '').strip() or None
        status = request.form.get('status', 'active')
        is_active = 1 if 'is_active' in request.form else 0
        
        if name:
            try:
                conn.execute('UPDATE projects SET name = ?, status = ?, is_active = ?, charging_code = ? WHERE id = ?', 
                    (name, status, is_active, charging_code, id))
                conn.commit()
            except sqlite3.IntegrityError:
                flash(f'Project name "{name}" is already in use.', 'error')
            except Exception as e:
                flash(f'An error occurred: {e}', 'error')
        
        conn.close()
        return redirect(url_for('projects_bp.projects'))
    
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if project is None:
        return "Project not found", 404
        
    return render_template('edit_project.html', project=project)

@projects_bp.route('/dashboard/<project_name>')
def project_dashboard(project_name):
    conn = get_db_connection()

    # Fetch project details (status, charging code)
    project_details = conn.execute(
        'SELECT * FROM projects WHERE name = ?', 
        (project_name,)
    ).fetchone()
    
    if project_details is None:
        conn.close()
        return "Project not found.", 404

    # Fetch Journal Entries for the Project
    journal_entries = conn.execute(
        'SELECT id, timestamp, content, duration_minutes, project FROM entries WHERE project = ? ORDER BY timestamp ASC',
        (project_name,)
    ).fetchall()

    entries_by_date = defaultdict(list)
    daily_project_totals = defaultdict(int)
    
    for entry in journal_entries:
        date_str = entry['timestamp'].split(' ')[0]
        
        # Group the entry
        entries_by_date[date_str].append(dict(entry))
        
        # Sum the duration_minutes for the total project time that day
        duration = entry['duration_minutes'] if entry['duration_minutes'] is not None else 0
        daily_project_totals[date_str] += duration

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
    completion_percentage = (finished_count / total_tasks * 100) if total_tasks > 0 else 0
    
    # Data Filtering for Template 
    return render_template(
        'project_dashboard.html',
        project_name=project_name,
        project=project_details,
        entries_by_date=reversed(entries_by_date.items()),
        daily_project_totals=daily_project_totals,
        active_todos=active_todos,
        finished_todos=finished_todos,
        total_tasks=total_tasks,
        completion_percentage=round(completion_percentage, 1)
    )