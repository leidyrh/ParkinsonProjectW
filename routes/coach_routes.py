from flask import Blueprint, render_template, session, redirect, url_for, request
from flask_mysqldb import MySQL

coach_bp = Blueprint('coach', __name__)
mysql = MySQL()

# Coach Dashboard Route
@coach_bp.route('/dashboard')
def dashboard():
    # Check if user is logged in as coach
    if 'logged_in' in session and session.get('role') == 'coach':
        return render_template('coach_dashboard.html')  # Render coach dashboard template
    else:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

# Route to View Patients Assigned to Coach
@coach_bp.route('/patients')
def view_patients():
    if 'logged_in' in session and session.get('role') == 'coach':
        # Fetch patients assigned to the coach from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM patients WHERE coach_id = %s", (session['user_id'],))
        patients = cur.fetchall()
        cur.close()
        return render_template('view_patients.html', patients=patients)  # Render patients list
    else:
        return redirect(url_for('login'))

# Route to View Patient Details
@coach_bp.route('/patient/<int:patient_id>')
def patient_details(patient_id):
    if 'logged_in' in session and session.get('role') == 'coach':
        # Fetch specific patient details
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient = cur.fetchone()
        cur.close()
        return render_template('patient_details.html', patient=patient)  # Render patient details
    else:
        return redirect(url_for('login'))

# Route to Send Message to Patient
@coach_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'logged_in' in session and session.get('role') == 'coach':
        message = request.form['message']
        patient_id = request.form['patient_id']
        # Store the message in the database (example structure)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO messages (coach_id, patient_id, message) VALUES (%s, %s, %s)",
                    (session['user_id'], patient_id, message))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('coach.view_patients'))  # Redirect to the patients list
    else:
        return redirect(url_for('login'))

# Route to Access Chat with a Specific Patient
@coach_bp.route('/chat/<int:patient_id>')
def chat_with_patient(patient_id):
    if 'logged_in' in session and session.get('role') == 'coach':
        return redirect(url_for('chat.chat', receiver_id=patient_id))  # Redirect to chat route
    else:
        return redirect(url_for('login'))

# Optional: Route for Logging Out
@coach_bp.route('/logout')
def logout():
    session.clear()  # Clear the session data
    return redirect(url_for('login'))  # Redirect to login page
