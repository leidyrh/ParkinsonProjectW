import MySQLdb
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import mysql
import pymysql

from routes.admin_classes_routes import manage_notification

# Create the Blueprint for patient-related routes
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

# Patient Dashboard
@patient_bp.route('/dashboard')
def patient_dashboard():
    """Displays the patient's dashboard."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    # Get the patient's information and notifications from the database
    cur = mysql.connection.cursor(pymysql.cursors.DictCursor)

    try:
        # Fetch the patient's information
        cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
        patient = cur.fetchone()
        if not patient:
            flash("Patient not found!", "danger")
            return redirect(url_for('home'))

        # Fetch unread notifications for the patient
        cur.execute("""
            SELECT notification_id, notification_type, message, notification_status, notification_date
            FROM notifications
            WHERE patient_id = %s AND notification_status != 'Read'
            ORDER BY notification_date DESC
            LIMIT 5
        """, (patient['patient_id'],))
        notifications = cur.fetchall()
    except pymysql.err.ProgrammingError as e:
        print("Error:", e)
        flash("An error occurred while fetching data.", "danger")
        return redirect(url_for('home'))
    finally:
        cur.close()

    return render_template('patient_dashboard.html', patient=patient, notifications=notifications)


@patient_bp.route('/mark_notification_as_read/<int:notification_id>', methods=['POST'])
def mark_notification_as_read(notification_id):
    """Marks a notification as read."""
    manage_notification(action='mark_as_read', notification_id=notification_id)
    return redirect(url_for('patient.patient_dashboard'))


# Edit Patient Profile
@patient_bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    """Allows patients to edit their profile information, except for mobility level."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    if request.method == 'POST':
        # Retrieve form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        emergency_contact_name = request.form.get('emergency_contact_name')
        emergency_contact_phone = request.form.get('emergency_contact_phone')
        health_condition = request.form.get('health_condition')

        # Validate required fields
        if not first_name or not last_name or not email:
            flash("First Name, Last Name, and Email are required.", "danger")
            return redirect(url_for('patient.edit_profile'))

        # Update the database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                UPDATE patients
                SET first_name = %s, last_name = %s, dob = %s, gender = %s, phone = %s,
                    email = %s, address = %s, emergency_contact_name = %s,
                    emergency_contact_phone = %s, health_condition = %s
                WHERE user_id = %s
            """, (first_name, last_name, dob, gender, phone, email, address,
                  emergency_contact_name, emergency_contact_phone, health_condition,
                  user_id))
            mysql.connection.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
        finally:
            cur.close()

        return redirect(url_for('patient.patient_dashboard'))

    # Retrieve current profile info
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
    patient = cur.fetchone()
    cur.close()

    return render_template('edit_profile.html', patient=patient)


# View Patient Appointments
@patient_bp.route('/appointments')
def view_appointments():
    """Display the list of appointments for the patient."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    # Retrieve the patient's appointments
    cur = mysql.connection.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM appointments WHERE patient_id = %s ORDER BY appointment_date ASC", (user_id,))
    appointments = cur.fetchall()
    cur.close()

    return render_template('appointments.html', appointments=appointments)

# View Available Classes
@patient_bp.route('/view_classes', methods=['GET'])
def view_classes():
    """Displays a list of available classes."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')

    cur = mysql.connection.cursor(pymysql.cursors.DictCursor)
    # Get the patient_id using user_id
    cur.execute("SELECT patient_id FROM patients WHERE user_id = %s", (user_id,))
    patient_record = cur.fetchone()
    patient_id = patient_record['patient_id'] if patient_record else None

    if not patient_id:
        flash("Patient record not found.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch classes and check if the patient is enrolled
    cur.execute("""
        SELECT c.*,
               CASE WHEN pc.patient_id IS NOT NULL THEN TRUE ELSE FALSE END AS booked,
               c.capacity AS remaining_capacity
        FROM classes c
        LEFT JOIN patient_classes pc ON c.class_id = pc.class_id AND pc.patient_id = %s
    """, (patient_id,))
    classes = cur.fetchall()
    cur.close()

    return render_template('patient_view_classes.html', classes=classes)


@patient_bp.route('/book_class', methods=['POST'])
def book_class():
    """Allows a patient to book a class and decreases the class capacity."""
    if 'role' not in session or session['role'] != 'patient':
        flash("Unauthorized access. Please log in as a patient.", "danger")
        return redirect(url_for('auth.login'))

    try:
        user_id = session.get('user_id')
        class_id = request.form.get('class_id')

        if not user_id or not class_id:
            flash("Invalid request. Missing user or class information.", "danger")
            return redirect(url_for('patient.view_classes'))

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Retrieve patient_id using user_id from the session
        cur.execute("SELECT patient_id FROM patients WHERE user_id = %s", (user_id,))
        patient_record = cur.fetchone()

        if not patient_record:
            flash("Patient record not found.", "danger")
            return redirect(url_for('patient.view_classes'))

        patient_id = patient_record['patient_id']

        # Check if the class is already booked
        cur.execute("SELECT * FROM patient_classes WHERE patient_id = %s AND class_id = %s", (patient_id, class_id))
        if cur.fetchone():
            flash("You have already booked this class.", "info")
            return redirect(url_for('patient.view_classes'))

        # Check class capacity
        cur.execute("SELECT capacity FROM classes WHERE class_id = %s", (class_id,))
        class_info = cur.fetchone()

        if not class_info:
            flash("Class not found.", "danger")
            return redirect(url_for('patient.view_classes'))

        if class_info['capacity'] <= 0:
            flash("The class is fully booked.", "danger")
            return redirect(url_for('patient.view_classes'))

        # Insert the booking into the database and decrease class capacity
        cur.execute("INSERT INTO patient_classes (patient_id, class_id) VALUES (%s, %s)", (patient_id, class_id))
        cur.execute("UPDATE classes SET capacity = capacity - 1 WHERE class_id = %s", (class_id,))
        mysql.connection.commit()
        flash("Class booked successfully!", "success")

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
    finally:
        cur.close()

    return redirect(url_for('patient.view_classes'))

@patient_bp.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    """Allows a patient to cancel a class booking and increases the class capacity."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    class_id = request.form.get('class_id')

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Retrieve patient_id using user_id from the session
        cur.execute("SELECT patient_id FROM patients WHERE user_id = %s", (user_id,))
        patient_record = cur.fetchone()

        if not patient_record:
            flash("Patient record not found.", "danger")
            return redirect(url_for('patient.view_classes'))

        patient_id = patient_record['patient_id']

        # Ensure the booking exists before attempting to delete it
        cur.execute("SELECT * FROM patient_classes WHERE patient_id = %s AND class_id = %s", (patient_id, class_id))
        if not cur.fetchone():
            flash("You are not registered for this class.", "info")
            return redirect(url_for('patient.view_classes'))

        # Remove the booking from the database and increase class capacity
        cur.execute("DELETE FROM patient_classes WHERE patient_id = %s AND class_id = %s", (patient_id, class_id))
        cur.execute("UPDATE classes SET capacity = capacity + 1 WHERE class_id = %s", (class_id,))
        mysql.connection.commit()
        flash("Class reservation canceled successfully!", "success")

    except Exception as e:
        flash(f"Error canceling reservation: {str(e)}", "danger")
    finally:
        cur.close()

    return redirect(url_for('patient.view_classes'))


# Track Symptoms
@patient_bp.route('/track_symptoms', methods=['GET', 'POST'])
def track_symptoms():
    """Allows patients to track symptoms."""
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    if request.method == 'POST':
        symptom = request.form.get('symptom')
        severity = request.form.get('severity')
        notes = request.form.get('notes')

        # Validate inputs
        if not symptom or not severity:
            flash("Symptom and severity are required.", "danger")
            return redirect(url_for('patient.track_symptoms'))

        # Insert the symptom into the database
        user_id = session.get('user_id')
        cur = mysql.connection.cursor(pymysql.cursors.DictCursor)
        try:
            cur.execute("""
                INSERT INTO symptoms (user_id, symptom, severity, notes, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (user_id, symptom, severity, notes))
            mysql.connection.commit()
            flash("Symptom tracked successfully!", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
        finally:
            cur.close()

        return redirect(url_for('patient.track_symptoms'))

    return render_template('patient_track_symptoms.html')


@patient_bp.route('/messages', methods=['GET', 'POST'])
def manage_patient_messages():
    # Ensure the user is logged in and is a patient
    if 'user_id' not in session or session.get('role') != 'patient':
        return "Unauthorized access", 403

    patient_id = session['user_id']
    action = request.args.get('action')

    # Render the HTML page for patient messages if no action is provided
    if request.method == 'GET' and action is None:
        return render_template('patient_messages.html')  # Render the HTML template

    # Handle fetching messages when action is 'fetch'
    if request.method == 'GET' and action == 'fetch':
        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # Fetch all messages where the patient is either the sender or the recipient
            cur.execute("""
                SELECT sender_id, recipient_id, content, timestamp
                FROM messages
                WHERE sender_id = %s OR recipient_id = %s
                ORDER BY timestamp ASC
            """, (patient_id, patient_id))
            messages = cur.fetchall()
            cur.close()

            # Format messages for output
            messages_list = [
                {
                    "sender_id": msg['sender_id'],
                    "recipient_id": msg['recipient_id'],
                    "content": msg['content'],
                    "timestamp": msg['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                }
                for msg in messages
            ]

            return jsonify(messages_list), 200

        except Exception as e:
            print("Error fetching messages:", e)
            return jsonify({"error": "Failed to fetch messages"}), 500

    # Handle fetching unique senders when action is 'get_senders'
    elif request.method == 'GET' and action == 'get_senders':
        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # Fetch unique users who sent messages to the patient
            cur.execute("""
                SELECT DISTINCT sender_id, users.username 
                FROM messages
                JOIN users ON messages.sender_id = users.user_id
                WHERE recipient_id = %s
            """, (patient_id,))
            senders = cur.fetchall()
            cur.close()

            return jsonify(senders), 200

        except Exception as e:
            print("Error fetching senders:", e)
            return jsonify({"error": "Failed to fetch senders"}), 500

    # Handle sending messages when action is 'send'
    if request.method == 'POST' and action == 'send':
        data = request.get_json()
        content = data.get('content')
        recipient_id = data.get('recipient_id')  # Get recipient_id from the request data

        if not content:
            return jsonify({"error": "Message content cannot be empty"}), 400
        if not recipient_id:
            return jsonify({"error": "Recipient ID is required"}), 400

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("""
                INSERT INTO messages (sender_id, recipient_id, content, timestamp)
                VALUES (%s, %s, %s, NOW())
            """, (patient_id, recipient_id, content))
            mysql.connection.commit()
            cur.close()

            return jsonify({"message": "Message sent successfully"}), 201
        except Exception as e:
            print("Error sending message:", e)
            return jsonify({"error": "Failed to send message"}), 500

    return jsonify({"error": "Invalid action or method"}), 400


