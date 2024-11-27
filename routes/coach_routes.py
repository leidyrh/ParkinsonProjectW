import MySQLdb
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from flask_mysqldb import MySQL

coach_bp = Blueprint('coach', __name__, url_prefix='/coach')
mysql = MySQL()

# Coach Dashboard Route
@coach_bp.route('/dashboard')
def coach_dashboard():
    """Displays the coach's dashboard."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as coach

    coach_id = session.get('user_id')

    # Get the coach's information from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM coach WHERE coach_id = %s", (coach_id,))
    coach = cur.fetchone()

    # Fetch classes assigned to the coach
    cur.execute(
        "SELECT * FROM classes WHERE coach_id = %s",
        (coach_id,))
    classes = cur.fetchall()

    # Fetch all patients from the classes assigned to this coach
    query = """
               SELECT DISTINCT p.patient_id, p.first_name, p.email
               FROM patients p
               JOIN patient_classes pc ON p.patient_id = pc.patient_id
               JOIN classes c ON pc.class_id = c.class_id
               WHERE c.coach_id = %s
           """
    cur.execute(query, (coach_id,))
    patients = cur.fetchall()
    cur.close()

    if not coach:
        flash("Coach not found!", "danger")
        return redirect(url_for('home'))

    return render_template('coach_dashboard.html', coach=coach, classes=classes,patients=patients )

@coach_bp.route('/create_assessment/<int:patient_id>', methods=['GET', 'POST'])
def create_assessment(patient_id):
    """Allows the coach to create an assessment for a specific patient."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as coach

    coach_id = session.get('user_id')

    # Handle POST request to create an assessment
    if request.method == 'POST':
        assessment_name = request.form.get('assessment_name')
        assessment_data = request.form.get('assessment_data')

        # Validate inputs
        if not assessment_name or not assessment_data:
            flash("All fields are required to create an assessment.", "warning")
            return redirect(url_for('coach.create_assessment', patient_id=patient_id))

        try:
            # Save assessment to the database
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO assessments (assessment_name, assessment_data, coach_id, patient_id)
                VALUES (%s, %s, %s, %s)
            """, (assessment_name, assessment_data, coach_id, patient_id))
            mysql.connection.commit()
            cur.close()

            flash("Assessment created successfully!", "success")
            return redirect(url_for('coach.coach_dashboard'))
        except Exception as e:
            print(f"Error creating assessment: {e}")
            flash("An error occurred while creating the assessment. Please try again.", "danger")
            return redirect(url_for('coach.create_assessment', patient_id=patient_id))

    try:
        cur = mysql.connection.cursor()

        # Fetch patient information
        cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cur.fetchone()

        if not patient:
            flash("Patient not found.", "danger")
            cur.close()
            return redirect(url_for('coach.coach_dashboard'))

    except Exception as e:
        print(f"Error while fetching data: {e}")
        flash("An error occurred while loading the page. Please try again.", "danger")
        return redirect(url_for('coach.coach_dashboard'))

    return render_template('create_assessment.html', patient=patient)

# View Patients in a Class
@coach_bp.route('/class/<int:class_id>/patients', methods=['GET'])
def view_class_patients(class_id):
    """View patients registered in a specific class."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth.login'))

    coach_id = session.get('user_id')

    # Verify if the class belongs to this coach
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM classes WHERE class_id = %s AND coach_id = %s",
        (class_id, coach_id)
    )
    assigned_class = cur.fetchone()

    if not assigned_class:
        flash("Class not found or unauthorized access.", "danger")
        return redirect(url_for('coach.coach_dashboard'))

    # Fetch the list of patients in the class
    cur.execute(
        """
        SELECT p.patient_id, p.first_name, p.email
        FROM patients p
        JOIN patient_classes pc ON p.patient_id = pc.patient_id
        WHERE pc.class_id = %s
        """,
        (class_id,)
    )
    patients = cur.fetchall()
    cur.close()

    return render_template('coach_view_class_patients.html', class_info=assigned_class, patients=patients)


@coach_bp.route('/manage_messages', methods=['GET', 'POST'])
def manage_messages():
    """Allows the coach to manage messages with patients registered in their classes."""
    if 'role' not in session or session['role'] != 'coach':
        flash("Unauthorized access. Please log in as a coach.", "danger")
        return redirect(url_for('auth.login'))

    action = request.args.get('action')
    patient_id = request.args.get('patient_id', type=int)
    coach_id = session['user_id']  # Get the logged-in coach ID

    if request.method == 'POST' and action == 'send':
        # Send a message
        data = request.get_json()
        content = data.get('content')

        # Validate input
        if not content or not patient_id:
            return jsonify({"error": "Invalid data"}), 400

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Verify the patient is in a class assigned to the coach
            cur.execute("""
                SELECT u.user_id
                FROM users u
                JOIN patients p ON u.user_id = p.user_id
                JOIN patient_classes pc ON p.patient_id = pc.patient_id
                JOIN classes c ON pc.class_id = c.class_id
                WHERE c.coach_id = %s AND p.patient_id = %s
            """, (coach_id, patient_id))
            user = cur.fetchone()

            if not user:
                return jsonify({"error": "Patient is not in your class"}), 403

            recipient_id = user['user_id']

            # Insert the message
            cur.execute("""
                INSERT INTO messages (sender_id, recipient_id, content, timestamp)
                VALUES (%s, %s, %s, NOW())
            """, (coach_id, recipient_id, content))
            mysql.connection.commit()
            cur.close()

            return jsonify({"message": "Message sent successfully"}), 201

        except Exception as e:
            print(f"Error inserting message: {e}")
            return jsonify({"error": "Failed to send message", "details": str(e)}), 500

    elif request.method == 'GET' and action == 'fetch' and patient_id:
        # Fetch messages between coach and a specific patient
        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # Verify the patient is in a class assigned to the coach
            cur.execute("""
                SELECT u.user_id
                FROM users u
                JOIN patients p ON u.user_id = p.user_id
                JOIN patient_classes pc ON p.patient_id = pc.patient_id
                JOIN classes c ON pc.class_id = c.class_id
                WHERE c.coach_id = %s AND p.patient_id = %s
            """, (coach_id, patient_id))
            user = cur.fetchone()

            if not user:
                return jsonify({"error": "Patient is not in your class"}), 403

            recipient_id = user['user_id']

            # Fetch messages
            cur.execute("""
                SELECT sender_id, recipient_id, content, timestamp 
                FROM messages 
                WHERE (sender_id = %s AND recipient_id = %s) 
                   OR (sender_id = %s AND recipient_id = %s)
                ORDER BY timestamp ASC
            """, (coach_id, recipient_id, recipient_id, coach_id))
            messages = cur.fetchall()
            cur.close()

            # Format messages for output
            messages_list = [
                {
                    "sender_id": msg['sender_id'],
                    "recipient_id": msg['recipient_id'],
                    "content": msg['content'],
                    "timestamp": msg['timestamp'].strftime("%m-%d-%Y %H:%M:%S")
                }
                for msg in messages
            ]

            return jsonify(messages_list), 200

        except Exception as e:
            print(f"Error fetching messages: {e}")
            return jsonify({"error": "Failed to fetch messages", "details": str(e)}), 500

    elif request.method == 'GET' and action is None:
        # Fetch the list of patients in the coach's classes for the sidebar
        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("""
                SELECT DISTINCT p.patient_id, p.first_name, p.email
                FROM patients p
                JOIN patient_classes pc ON p.patient_id = pc.patient_id
                JOIN classes c ON pc.class_id = c.class_id
                WHERE c.coach_id = %s
            """, (coach_id,))
            patients = cur.fetchall()
            cur.close()

            # Render the messaging interface
            return render_template('coach_messages.html', patients=patients)
        except Exception as e:
            print(f"Error fetching patients: {e}")
            flash("An error occurred while loading the messaging page.", "danger")
            return redirect(url_for('coach.coach_dashboard'))

    return jsonify({"error": "Invalid request"}), 400

@coach_bp.route('/view_patient_assessments/<int:patient_id>', methods=['GET', 'POST'])
def view_patient_assessments(patient_id):
    """Displays and optionally edits assessments for a patient."""
    if 'role' not in session or session['role'] != 'coach':
        flash("Unauthorized access. Please log in as a coach.", "danger")
        return redirect(url_for('auth.login'))

    coach_id = session['user_id']
    assessment_id = request.args.get('assessment_id', type=int)  # Optional assessment ID for details

    if request.method == 'POST':
        # Handle editing an assessment
        assessment_id = request.form.get('assessment_id')
        assessment_name = request.form.get('assessment_name')
        assessment_data = request.form.get('assessment_data')

        if not assessment_id or not assessment_name or not assessment_data:
            flash("All fields are required to update the assessment.", "warning")
            return redirect(url_for('coach.view_patient_assessments', patient_id=patient_id, assessment_id=assessment_id))

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            # Ensure the assessment belongs to this coach and patient
            cur.execute("""
                SELECT id
                FROM assessments
                WHERE id = %s AND patient_id = %s AND coach_id = %s
            """, (assessment_id, patient_id, coach_id))
            assessment = cur.fetchone()

            if not assessment:
                flash("Assessment not found or unauthorized access.", "danger")
                return redirect(url_for('coach.view_patient_assessments', patient_id=patient_id))

            # Update the assessment
            cur.execute("""
                UPDATE assessments
                SET assessment_name = %s, assessment_data = %s, timestamp = NOW()
                WHERE id = %s
            """, (assessment_name, assessment_data, assessment_id))
            mysql.connection.commit()
            cur.close()

            flash("Assessment updated successfully!", "success")
            return redirect(url_for('coach.view_patient_assessments', patient_id=patient_id, assessment_id=assessment_id))

        except Exception as e:
            print(f"Error updating assessment: {e}")
            flash("An error occurred while updating the assessment.", "danger")
            return redirect(url_for('coach.view_patient_assessments', patient_id=patient_id, assessment_id=assessment_id))

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Validate if the patient belongs to a class assigned to the coach
        cur.execute("""
            SELECT p.patient_id, p.first_name
            FROM patients p
            JOIN patient_classes pc ON p.patient_id = pc.patient_id
            JOIN classes c ON pc.class_id = c.class_id
            WHERE c.coach_id = %s AND p.patient_id = %s
        """, (coach_id, patient_id))
        patient = cur.fetchone()

        if not patient:
            flash("This patient is not assigned to you.", "danger")
            return redirect(url_for('coach.coach_dashboard'))

        # If an assessment ID is provided, fetch its details
        assessment = None
        if assessment_id:
            cur.execute("""
                SELECT id, assessment_name, assessment_data, submitted_at
                FROM assessments
                WHERE id = %s AND patient_id = %s AND coach_id = %s
            """, (assessment_id, patient_id, coach_id))
            assessment = cur.fetchone()

            if not assessment:
                flash("Assessment not found or unauthorized access.", "danger")
                return redirect(url_for('coach.view_patient_assessments', patient_id=patient_id))

        # Fetch all assessments for the patient if no specific assessment is selected
        cur.execute("""
            SELECT id, assessment_name, submitted_at
            FROM assessments
            WHERE patient_id = %s AND coach_id = %s
            ORDER BY submitted_at DESC
        """, (patient_id, coach_id))
        assessments = cur.fetchall()
        cur.close()

        return render_template(
            'view_assessments.html',
            patient=patient,
            assessments=assessments,
            assessment=assessment
        )

    except Exception as e:
        print(f"Error: {e}")
        flash("An error occurred while fetching assessments.", "danger")
        return redirect(url_for('coach.coach_dashboard'))

@coach_bp.route('/logout')
def logout():
    """Logs the user out."""
    session.clear()  # Clear the session data
    return redirect(url_for('auth.login'))  # Redirect to login page
