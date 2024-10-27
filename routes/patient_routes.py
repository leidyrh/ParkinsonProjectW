from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app

from app import mysql
# Create the Blueprint for patient-related routes
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')


# Patient Dashboard
@patient_bp.route('/dashboard')
def patient_dashboard():
    """Displays the patient's dashboard."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    # Get the patient's information from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
    patient = cur.fetchone()

    if not patient:
        flash("Patient not found!", "danger")
        return redirect(url_for('home'))

    return render_template('patient_dashboard.html', patient=patient)


# Edit Patient Profile
@patient_bp.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    """Allows patients to edit their profile information."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']

        # Validate inputs
        if not name or not age or not gender:
            flash("All fields are required.", "danger")
            return redirect(url_for('patient.edit_profile'))

        # Update the patient's profile information in the database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                UPDATE patients 
                SET name = %s, age = %s, gender = %s
                WHERE user_id = %s
            """, (name, age, gender, user_id))
            mysql.connection.commit()

            flash("Profile updated successfully!", "success")
            return redirect(url_for('patient.patient_dashboard'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('patient.edit_profile'))

    # Retrieve current profile info
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
    patient = cur.fetchone()

    return render_template('edit_profile.html', patient=patient)


# View Patient Appointments (if applicable)
@patient_bp.route('/appointments')
def view_appointments():
    """Display the list of appointments for the patient."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    # Retrieve the patient's appointments
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM appointments WHERE patient_id = %s", (user_id,))
    appointments = cur.fetchall()

    return render_template('appointments.html', appointments=appointments)


# Book an Appointment (if applicable)
@patient_bp.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    """Allows patients to book an appointment."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    if request.method == 'POST':
        coach_id = request.form['coach_id']
        appointment_date = request.form['appointment_date']

        # Validate inputs
        if not coach_id or not appointment_date:
            flash("Both coach and appointment date are required.", "danger")
            return redirect(url_for('patient.book_appointment'))

        # Insert the appointment into the database
        user_id = session.get('user_id')
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO appointments (patient_id, coach_id, appointment_date)
                VALUES (%s, %s, %s)
            """, (user_id, coach_id, appointment_date))
            current_app.mysql.connection.commit()

            flash("Appointment booked successfully!", "success")
            return redirect(url_for('patient.view_appointments'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('patient.book_appointment'))

    # Get available coaches for booking an appointment
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE role = 'coach'")
    coaches = cur.fetchall()

    return render_template('book_appointment.html', coaches=coaches)
# Chat Room route (if separate from the admin chat)
@patient_bp.route('/chat')
def chat():
    if 'logged_in' in session and session.get('role') == 'patient':
        return render_template('chat_room.html')  # Render the chat room template
    else:
        return redirect(url_for('login'))

