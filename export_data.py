from flask import Blueprint, render_template, send_file, request, redirect, url_for, flash, render_template
import datetime
import io
import csv
import zipfile
import datetime
import sqlite3

export_data_bp = Blueprint('export_data_bp', __name__)

# Helper function to get database connection (copied from app.py)
def get_db_connection():
    conn = sqlite3.connect('journal.db')
    conn.row_factory = sqlite3.Row
    return conn

@export_data_bp.route('/export', methods=['GET', 'POST'])
def export_data():
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not start_date_str or not end_date_str:
            flash("Please select both a start and an end date.", 'error')
            return redirect(url_for('export_data'))

        # Ensure end date is inclusive by adding one day to the filter range
        end_date_inclusive = (datetime.datetime.strptime(end_date_str, '%Y-%m-%d') + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        conn = get_db_connection()

        # Fetch Entries
        entries = conn.execute(
            'SELECT timestamp, project, content FROM entries WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp',
            (start_date_str, end_date_inclusive)
        ).fetchall()

        # Fetch Finished Todos (Using finished_date)
        finished_todos = conn.execute(
            'SELECT finished_date, project, item, start_date, due_date, priority FROM todos WHERE finished_date >= ? AND finished_date < ? AND status = "finished" ORDER BY finished_date',
            (start_date_str, end_date_inclusive)
        ).fetchall()
        
        conn.close()

        # Create an in-memory zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:

            # CSV 1: ENTRIES 
            entries_output = io.StringIO()
            writer = csv.writer(entries_output)
            writer.writerow(['Timestamp', 'Project', 'Content']) # Header
            for row in entries:
                writer.writerow(tuple(row))
            
            # Write the CSV file to the zip archive
            zf.writestr('journal_entries.csv', entries_output.getvalue())

            # CSV 2: FINISHED TODOS
            todos_output = io.StringIO()
            writer = csv.writer(todos_output)
            writer.writerow(['Finished Date', 'Project', 'Task', 'Started', 'Due', 'Priority']) # Header
            for row in finished_todos:
                writer.writerow(tuple(row))
            
            # Write the CSV file to the zip archive
            zf.writestr('finished_todos.csv', todos_output.getvalue())

        zip_buffer.seek(0)
        
        # Send the zipped file back to the user
        filename = f'project_echo_export_{start_date_str}_to_{end_date_str}.zip'
        return send_file(zip_buffer, 
                         mimetype='application/zip', 
                         as_attachment=True, 
                         download_name=filename)
    
    # Render the date selection form for GET requests
    return render_template('export.html')
