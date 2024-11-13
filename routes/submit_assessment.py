from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_mysqldb import MySQL

coach_bp = Blueprint('coach', __name__, url_prefix='/coach')
mysql = MySQL()

from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_mysqldb import MySQL
from datetime import datetime

coach_bp = Blueprint('coach', __name__, url_prefix='/coach')
mysql = MySQL()


# Submit Assessment Route
@coach_bp.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    """Handles the submission of an assessment."""
    assessment_data = request.form['assessment_data']
    patient_id = request.form['patient_id']
    document_id = request.form['assessment_name']  # Referring to the document ID from the dropdown

    # Get the coach's user_id from the session
    coach_id = session['user_id']

    # Get the current timestamp for the submission
    submitted_at = datetime.now()

    # Insert the assessment into the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO assessments (assessment_data, patient_id, coach_id, submitted_at, document_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (assessment_data, patient_id, coach_id, submitted_at, document_id))
    mysql.connection.commit()
    cur.close()

    flash('Assessment submitted successfully!', 'success')
    return redirect(url_for('coach.coach_dashboard'))

