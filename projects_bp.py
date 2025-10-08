# projects_bp.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
# Assume get_db_connection is available (you'll need to import it or define it here)

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