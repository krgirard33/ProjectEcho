from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
import datetime
from utilities import calculate_next_due_date

recurring_bp = Blueprint('recurring_bp', __name__, url_prefix='/recurring')

DB_NAME = 'journal.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@recurring_bp.route('/', methods=('GET', 'POST'))
def manage_recurring():
    conn = get_db_connection()
    
    if request.method == 'POST':
        item = request.form['item'].strip()
        project = request.form.get('project') or None
        recurrence_type = request.form['recurrence_type']
        next_due_date = request.form['next_due_date']
        
        if item and recurrence_type and next_due_date:
            conn.execute(
                'INSERT INTO recurring_todos (item, project, recurrence_type, next_due_date) VALUES (?, ?, ?, ?)',
                (item, project, recurrence_type, next_due_date)
            )
            conn.commit()
            flash('Recurring To-Do added successfully!', 'success')
        else:
            flash('Please fill out all required fields.', 'error')
        
        return redirect(url_for('recurring_bp.manage_recurring'))
    
    # GET Request: Fetch all recurring todos and active projects
    recurring_items = conn.execute(
        'SELECT * FROM recurring_todos ORDER BY is_active DESC, next_due_date ASC'
    ).fetchall()
    active_projects = [row['name'] for row in conn.execute('SELECT name FROM projects WHERE is_active = 1').fetchall()]
    conn.close()
    
    return render_template('recurring_todos.html', 
                           recurring_items=recurring_items, 
                           active_projects=active_projects)

@recurring_bp.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit_recurring(id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        item = request.form['item'].strip()
        project = request.form.get('project') or None
        recurrence_type = request.form['recurrence_type']
        next_due_date = request.form['next_due_date']
        is_active = 1 if 'is_active' in request.form else 0
        
        if item and recurrence_type and next_due_date:
            conn.execute(
                'UPDATE recurring_todos SET item = ?, project = ?, recurrence_type = ?, next_due_date = ?, is_active = ? WHERE id = ?',
                (item, project, recurrence_type, next_due_date, is_active, id)
            )
            conn.commit()
            flash('Recurring To-Do updated successfully!', 'success')
        else:
            flash('Please fill out all required fields.', 'error')
        
        conn.close()
        return redirect(url_for('recurring_bp.manage_recurring'))

    # GET Request: Fetch item details
    recurring_item = conn.execute('SELECT * FROM recurring_todos WHERE id = ?', (id,)).fetchone()
    active_projects = [row['name'] for row in conn.execute('SELECT name FROM projects WHERE is_active = 1').fetchall()]
    conn.close()
    
    if recurring_item is None:
        return "Recurring To-Do not found", 404
        
    # Pass the single item object to the template as 'item'
    return render_template('edit_recurring.html', item=recurring_item, active_projects=active_projects)