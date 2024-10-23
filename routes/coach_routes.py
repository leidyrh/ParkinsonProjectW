from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app

from app import mysql

# Create the Blueprint for coach-related routes
coach_bp = Blueprint('coach', __name__, url_prefix='/coach')


# Coach Dashboard (Viewing Patients, Appointments, etc.)
@coach_bp.route('/dashboard')
def coach_dashboard():
    """Displays the coach's dashboard."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth_routes.login'))  # Redirect to login if not authenticated as coach

    user_id = session.get('user_id')

    # Get the coach's information and list of patients assigned to the coach
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM users
        WHERE user_id = %s AND role = 'coach'
    """, (user_id,))
    coach = cur.fetchone()

    if not coach:
        flash("Coach not found!", "danger")
        return redirect(url_for('home'))

    # Get list of patients assigned to this coach (from appointments)
    cur.execute("""
        SELECT DISTINCT p.user_id, p.name, p.age, p.gender 
        FROM appointments a
        JOIN patients p ON a.patient_id = p.user_id
        WHERE a.coach_id = %s
    """, (user_id,))
    patients = cur.fetchall()

    return render_template('coach_dashboard.html', coach=coach, patients=patients)


# View a Coach's Appointments (Sessions with Patients)
@coach_bp.route('/appointments')
def coach_appointments():
    """Displays the coach's upcoming appointments."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth_routes.login'))  # Redirect to login if not authenticated as coach

    user_id = session.get('user_id')

    # Get the coach's upcoming appointments with patients
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.id, p.name, a.appointment_date 
        FROM appointments a
        JOIN patients p ON a.patient_id = p.user_id
        WHERE a.coach_id = %s AND a.appointment_date > NOW()
    """, (user_id,))
    appointments = cur.fetchall()

    return render_template('appointments.html', appointments=appointments)


# Edit Coach Profile
@coach_bp.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    """Allows coaches to edit their profile information."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as coach

    user_id = session.get('user_id')

    if request.method == 'POST':
        name = request.form['name']
        specialty = request.form['specialty']
        bio = request.form['bio']

        # Validate inputs
        if not name or not specialty or not bio:
            flash("All fields are required.", "danger")
            return redirect(url_for('coach.edit_profile'))

        # Update the coach's profile information
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                UPDATE users 
                SET name = %s, specialty = %s, bio = %s
                WHERE user_id = %s AND role = 'coach'
            """, (name, specialty, bio, user_id))
            current_app.mysql.connection.commit()

            flash("Profile updated successfully!", "success")
            return redirect(url_for('coach.coach_dashboard'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('coach.edit_profile'))

    # Retrieve current profile info
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT name, specialty, bio 
        FROM users 
        WHERE user_id = %s AND role = 'coach'
    """, (user_id,))
    coach = cur.fetchone()

    return render_template('edit_profile.html', coach=coach)


# Manage Patient Appointments (if a coach can reschedule or cancel appointments)
@coach_bp.route('/manage_appointments/<int:appointment_id>', methods=['GET', 'POST'])
def manage_appointment(appointment_id):
    """Allows a coach to manage (e.g., reschedule or cancel) an appointment."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as coach

    user_id = session.get('user_id')

    # Fetch appointment details
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.appointment_date, p.name 
        FROM appointments a
        JOIN patients p ON a.patient_id = p.user_id
        WHERE a.id = %s AND a.coach_id = %s
    """, (appointment_id, user_id))
    appointment = cur.fetchone()

    if not appointment:
        flash("Appointment not found or you are not authorized to manage this appointment.", "danger")
        return redirect(url_for('coach.coach_dashboard'))

    if request.method == 'POST':
        action = request.form['action']  # 'Reschedule' or 'Cancel'
        if action == 'Reschedule':
            new_date = request.form['new_date']
            cur.execute("""
                UPDATE appointments
                SET appointment_date = %s
                WHERE id = %s
            """, (new_date, appointment_id))
            mysql.connection.commit()
            flash("Appointment rescheduled successfully!", "success")
        elif action == 'Cancel':
            cur.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
            mysql.connection.commit()
            flash("Appointment cancelled successfully!", "success")

        return redirect(url_for('coach.coach_appointments'))

    return render_template('manage_appointment.html', appointment=appointment)

