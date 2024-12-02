import MySQLdb
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import generate_password_hash
from app import mysql
from routes.auth_routes import is_valid_username, is_valid_email, is_strong_password
from datetime import datetime



admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# Admin Dashboard route
@admin_bp.route('/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session:
        flash('You must be logged in to access the admin dashboard.', 'warning')
        return redirect(url_for('auth.login'))  # Redirect to login if not logged in

    # Get the user's role from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT role FROM users WHERE user_id = %s", (session['user_id'],))
    user = cur.fetchone()

    # Fetch counts
    cur.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'patient'")
    patient_count = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'coach'")
    coach_count = cur.fetchone()['count']

    if user and user['role'] == 'admin':
        # Retrieve all users from the database
        cur.execute("SELECT user_id, username, role FROM users")
        users = cur.fetchall()

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'create_patient':
                # Create a new patient
                username = request.form['username']
                password = request.form['password']
                email = request.form['email']
                role = 'patient'

                # Validate input using regular expressions
                if not is_valid_username(username):
                    flash("Invalid username! It should be alphanumeric and between 3 to 15 characters.", "danger")
                    return redirect(url_for('admin.admin_dashboard'))

                if not is_valid_email(email):
                    flash("Invalid email format!", "danger")
                    return redirect(url_for('admin.admin_dashboard'))

                if not is_strong_password(password):
                    flash(
                        "Password is too weak! It should be at least 8 characters long, contain a number, and a special character.",
                        "danger")
                    return redirect(url_for('admin.admin_dashboard'))

                # Generate a password hash
                # Hash the password before storing it
                hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                # Insert user into the database
                # cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                            (username, hashed_pw.decode('utf-8'), email, role))  # Role 'patient' by default for simplicity
                mysql.connection.commit()
                # Get the user_id of the newly created user
                user_id = cur.lastrowid

                # After inserting into the users table, also insert into the patients table
                cur.execute("INSERT INTO patients (user_id,username, password, email) VALUES (%s, %s, %s,%s)",
                            (user_id, username, hashed_pw.decode('utf-8'), email))
                mysql.connection.commit()

                flash('New user created successfully!', 'success')

            elif action == 'assign_role':
                # Assign a new role to an existing user
                user_id = request.form['user_id']
                new_role = request.form['new_role']
                MAX_ADMINS = 5

                if new_role == 'admin':
                    # Check if there are already enough admins
                    cur.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'")
                    admin_count = cur.fetchone()['admin_count']

                    if admin_count >= MAX_ADMINS:
                        flash(f'Cannot assign more than {MAX_ADMINS} admins.', 'danger')
                        return redirect(url_for('admin.admin_dashboard'))

                elif new_role == 'patient':
                    try:
                        # Check if the user exists
                        cur.execute("SELECT role, username FROM users WHERE user_id = %s", (user_id,))
                        user_data = cur.fetchone()

                        if not user_data:
                            flash("User not found.", "danger")
                            return redirect(url_for('admin.admin_dashboard'))

                        current_role, username = user_data

                        # Remove from coach table if the user is currently a coach
                        if current_role == 'coach':
                            cur.execute("DELETE FROM coach WHERE coach_id = %s", (user_id,))
                            flash("User removed from coach role.", "info")

                        # Insert into patients table if not already a patient
                        cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
                        if not cur.fetchone():
                            cur.execute("INSERT INTO patients (user_id, username) VALUES (%s, %s)", (user_id, username))
                            flash("Patient role assigned successfully!", "success")
                        else:
                            flash("This user is already a member.", "info")

                        # Update the role in the `users` table
                        cur.execute("UPDATE users SET role = %s WHERE user_id = %s", ('patient', user_id))
                        mysql.connection.commit()  # Commit all changes

                    except Exception as e:
                        mysql.connection.rollback()  # Rollback if any error occurs
                        flash("An error occurred while updating the user role.", "danger")
                        print("Error:", e)


                elif new_role == 'coach':
                    # Check if the user is currently a patient and remove them from the `patients` table
                    cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
                    existing_patient = cur.fetchone()

                    if existing_patient:
                        try:
                            cur.execute("DELETE FROM patients WHERE user_id = %s", (user_id,))
                            mysql.connection.commit()
                            flash("User removed from member role.", "info")
                        except Exception as e:
                            mysql.connection.rollback()
                            flash("An error occurred while removing the member role.", "danger")
                            print("Error:", e)
                            return redirect(url_for('admin.manage_classes'))

                    # Check if the user is already a coach
                    cur.execute("SELECT * FROM coach WHERE coach_id = %s", (user_id,))
                    existing_coach = cur.fetchone()

                    if existing_coach:
                        flash("This user is already a coach.", "info")
                    else:
                        try:
                            # Insert user into coach table
                            cur.execute(
                                "INSERT INTO coach (coach_id, username) SELECT user_id, username FROM users WHERE user_id = %s",
                                (user_id,))
                            mysql.connection.commit()  # Commit the transaction
                            flash("Coach role assigned successfully!", "success")
                        except Exception as e:
                            mysql.connection.rollback()  # Rollback in case of error
                            flash("An error occurred while assigning the coach role.", "danger")
                            print("Error:", e)
                            return redirect(url_for('admin.manage_classes'))

                    # Update the role in the `users` table to 'coach'
                    try:
                        cur.execute("UPDATE users SET role = %s WHERE user_id = %s", ('coach', user_id))
                        mysql.connection.commit()  # Commit the transaction

                    except Exception as e:
                        mysql.connection.rollback()  # Rollback in case of error
                        flash("An error occurred while updating the user role.", "danger")
                        print("Error:", e)

                # Commit transaction and update role in users table
                mysql.connection.commit()
                cur.execute("UPDATE users SET role = %s WHERE user_id = %s", (new_role, user_id))
                mysql.connection.commit()
                flash('User role updated successfully!', 'success')

            elif action == 'delete_user':
                # Delete user by ID
                user_id = request.form['user_id']
                cur = mysql.connection.cursor()
                cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                mysql.connection.commit()

                flash('User deleted successfully!', 'success')

            # Re-fetch the updated list of users after the action
            cur.execute("SELECT user_id, username, role FROM users")
            users = cur.fetchall()

            # Re-render the page with the updated user list
            return render_template('admin_dashboard.html', users=users)

        # After handling each action, re-fetch the updated patient lists. NEEDED FOR MESSAGING LR
        cur.execute("""
                            SELECT users.user_id, users.username, users.email, patients.first_name, patients.dob,patients.gender, patients.phone, patients.address, patients.health_condition
                                FROM users
                                JOIN patients ON users.user_id = patients.user_id
                                WHERE users.role = 'patient'
                            """)
        patients = cur.fetchall()
        # # Debugging statement
        # print("Fetched patients:", patients)
        cur.close()

        return render_template('admin_dashboard.html', users=users, patients=patients, patient_count=patient_count, coach_count=coach_count)

    else:
        flash('You do not have permission to access the admin dashboard.', 'danger')
        return redirect(url_for('patient.patient_dashboard'))  # Redirect if not admin

@admin_bp.route('/edit_user', methods=['POST'])
def edit_user():
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = request.form['user_id']
    username = request.form['username']
    password = request.form['password']

    # Validate new username and password (using your existing validation functions)
    if not is_valid_username(username):
        flash("Invalid username! It should be alphanumeric and between 3 to 15 characters.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    if not is_strong_password(password):
        flash("Password is too weak! It should be at least 8 characters long, contain a number, and a special character.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    # Hash the new password
    password = generate_password_hash(password)

    # Update the user's username and password in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET username = %s, password = %s WHERE user_id = %s", (username, password, user_id))
    mysql.connection.commit()

    flash('User information updated successfully!', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/edit_patient/<int:user_id>', methods=['GET', 'POST'])
def edit_patient_profile(user_id):
    # Ensure the user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("You must be an admin to access this page.", "warning")
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        # Retrieve form data, including date of birth
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        #age = request.form['age']
        dob = request.form['dob']  # New field
        gender = request.form['gender']
        phone = request.form['phone']
        address = request.form['address']
        medical_history = request.form['health_condition']

        # Update the `users` and `patients` tables
        try:
            # Update the users table
            cur.execute("""
                UPDATE users 
                SET username = %s, email = %s 
                WHERE user_id = %s
            """, (username, email, user_id))

            # Update the patients table
            cur.execute("""
                UPDATE patients 
                SET first_name = %s, dob = %s, gender = %s, 
                    phone = %s, address = %s, health_condition = %s 
                WHERE user_id = %s
            """, (first_name, dob, gender, phone, address, medical_history, user_id))

            mysql.connection.commit()
            flash("Member profile updated successfully!", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash("An error occurred while updating the member profile.", "danger")
            print(e)

    # Fetch updated patient information for rendering
    cur.execute("""
        SELECT users.user_id, users.username, users.email, patients.first_name, 
               patients.dob, patients.gender, patients.phone, patients.address, 
               patients.health_condition
        FROM users
        JOIN patients ON users.user_id = patients.user_id
        WHERE users.user_id = %s
    """, (user_id,))
    patient = cur.fetchone()
    cur.close()

    if not patient:
        flash("Member not found.", "danger")
        return redirect(url_for('admin.admin_patients_list'))

    return render_template('admin_patient_profile.html', patient=patient)

# Route to list all patients
@admin_bp.route('/patients')
def list_patients():
    # Retrieve all patients from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
            SELECT users.user_id, users.username, users.email, patients.first_name, patients.dob, 
                   patients.gender, patients.phone, patients.address, patients.health_condition
            FROM users
            JOIN patients ON users.user_id = patients.user_id
            WHERE users.role = 'patient'
        """)
    patients = cur.fetchall()
    cur.close()
    return render_template('admin_patients_list.html', patients=patients)

# Route to list all coaches
@admin_bp.route('/list_coaches', methods=['GET'])
def list_coaches():
    # Retrieve all patients from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
            SELECT users.user_id, users.username, users.email, coach.first_name, coach.last_name, coach.specialization, 
                   coach.phone
            FROM users
            JOIN coach ON users.user_id = coach.coach_id
            WHERE users.role = 'coach'
        """)
    coaches = cur.fetchall()
    cur.close()
    return render_template('admin_coaches_list.html', coaches=coaches)

@admin_bp.route('/view_patient/<int:user_id>')
def view_patient_profile(user_id):
    # Ensure the user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("You must be an admin to access this page.", "warning")
        return redirect(url_for('auth.login'))

    # Fetch patient information from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT users.user_id,users.username, users.email, patients.first_name, patients.dob, 
               patients.gender, patients.phone, patients.address, 
               patients.health_condition
        FROM users
        JOIN patients ON users.user_id = patients.user_id
        WHERE users.user_id = %s
    """, (user_id,))
    patient = cur.fetchone()  # Use `fetchone()` since we're retrieving a single patient
    cur.close()

    # Check if the patient was found
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    # Pass `patient` to the template, not `patients`
    return render_template('admin_patient_profile.html', patient=patient)

@admin_bp.route('/edit_coach/<int:user_id>', methods=['GET', 'POST'])
def edit_coach_profile(user_id):
    # Ensure the user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("You must be an admin to access this page.", "warning")
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        # Retrieve form data, including date of birth
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        specialization = request.form['specialization']

        try:
            # Update the users table
            cur.execute("""
                UPDATE users 
                SET username = %s, email = %s 
                WHERE user_id = %s
            """, (username, email, user_id))

            # Update the coach table
            cur.execute("""
                UPDATE coach 
                SET first_name = %s, last_name = %s, specialization = %s, 
                    phone = %s 
                WHERE coach_id = %s
            """, ( first_name,last_name, specialization,phone, user_id))

            mysql.connection.commit()
            flash("Coach profile updated successfully!", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash("An error occurred while updating the coach profile.", "danger")
            print(e)

    # Fetch updated coach information for rendering
    cur.execute("""
        SELECT users.user_id, users.username, users.email, coach.first_name, 
               coach.last_name, coach.specialization, coach.phone 
        FROM users
        JOIN coach ON users.user_id = coach.coach_id
        WHERE users.user_id = %s
    """, (user_id,))
    coach = cur.fetchone()
    cur.close()

    if not coach:
        flash("Member not found.", "danger")
        return redirect(url_for('admin.admin_coach_list'))

    return render_template('admin_coach_profile.html', coach=coach)

@admin_bp.route('/messages', methods=['GET', 'POST'])
def manage_messages():
    action = request.args.get('action')
    patient_id = request.args.get('patient_id', type=int)

    if request.method == 'POST' and action == 'send':
        # Send a message
        data = request.get_json()
        content = data.get('content')
        sender_id = session['user_id']  # Assuming the admin's user ID is in the session

        #print(f"Attempting to send message: {content} to patient_id: {patient_id}")
        print("Attempting to send message:")
        print("Content:", content)
        print("Sender ID:", sender_id)
        print("Recipient ID:", patient_id)

        if not content or not patient_id:
            return jsonify({"error": "Invalid data"}), 400

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("""
                    INSERT INTO messages (sender_id, recipient_id, content, timestamp)
                    VALUES (%s, %s, %s, NOW())
                """, (sender_id, patient_id, content))
            mysql.connection.commit()
            print("Commit successful")  # Debugging output
            cur.close()

            print("Message sent successfully")
        except Exception as e:
            print("Error inserting message:", e)
            return jsonify({"error": "Failed to insert message", "details": str(e)}), 500

        return jsonify({"message": "Message sent successfully"}), 201

    elif request.method == 'GET' and action == 'fetch' and patient_id:
        # Fetch messages between admin and a specific patient
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT sender_id, recipient_id, content, timestamp 
            FROM messages 
            WHERE (sender_id = %s AND recipient_id = %s) 
               OR (sender_id = %s AND recipient_id = %s)
            ORDER BY timestamp ASC
        """, (session['user_id'], patient_id, patient_id, session['user_id']))
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

    # Render the admin_messages.html template on a basic GET request (without action parameter)
    if request.method == 'GET' and action is None:
        # Fetch the list of patients for the sidebar
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT users.user_id, users.username, users.email, patients.first_name 
            FROM users 
            JOIN patients ON users.user_id = patients.user_id 
            WHERE users.role = 'patient'
        """)
        patients = cur.fetchall()
        cur.close()

        # Pass the list of patients to the template for rendering the sidebar
        return render_template('admin_messages.html', patients=patients)




