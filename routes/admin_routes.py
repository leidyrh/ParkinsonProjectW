import MySQLdb
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash
from app import mysql
from routes.auth_routes import is_valid_username, is_valid_email, is_strong_password


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

                flash('New patient created successfully!', 'success')

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
                    # Check if the patient record already exists
                    cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id))
                    existing_patient = cur.fetchone()

                    if existing_patient:
                        flash("This user is already a patient.", "info")
                    else:
                        # Insert user into patients table
                        cur.execute("INSERT INTO patients (user_id) VALUES (%s)", (user_id,))
                        flash("Patient role assigned successfully!", "success")

                elif new_role == 'coach':
                    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

                    # Fetch the username from the `users` table
                    cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
                    user = cur.fetchone()

                    if not user:
                        flash("User not found.", "danger")
                        return redirect(url_for('admin.manage_classes'))

                    username = user['username']

                    # Check if the username already exists in the `coach` table
                    cur.execute("SELECT * FROM coach WHERE username = %s", (username,))
                    existing_coach = cur.fetchone()

                    if existing_coach:
                        flash("This user is already assigned as a coach or the username is already in use.", "danger")
                        return redirect(url_for('admin.manage_classes'))

                    # Insert the new coach
                    try:
                        cur.execute("""
                                    INSERT INTO coach (user_id, username)
                                    VALUES (%s, %s)
                                """, (user_id, username))
                        mysql.connection.commit()
                        flash("User successfully assigned as a coach!", "success")
                    except Exception as e:
                        mysql.connection.rollback()
                        flash("An error occurred while assigning the role.", "danger")
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

        return render_template('admin_dashboard.html', users=users)

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
            flash("Patient profile updated successfully!", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash("An error occurred while updating the patient profile.", "danger")
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
        flash("Patient not found.", "danger")
        return redirect(url_for('admin.admin_patients_list'))

    return render_template('admin_patient_profile.html', patient=patient)

# Route to list all patients
@admin_bp.route('/patients')
def list_patients():
    # Retrieve all patients from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
            SELECT users.user_id, users.username, users.email, patients.first_name, patients.dob, 
                   patients.gender, patients.phone, patients.address
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
            JOIN coach ON users.user_id = coach.user_id
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

@admin_bp.route('/classes', methods=['GET', 'POST'])
def manage_classes():
    # Ensure the user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("You must be an admin to access this page.", "warning")
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check if the request is for adding a class or registering a patient
    if request.method == 'POST':
        if 'add_class' in request.form:  # Adding a new class

            class_name = request.form['class_name']
            description = request.form['description']
            level = request.form['level']
            duration = request.form['duration']
            start_time = request.form['start_time']
            capacity = request.form['capacity']
            coach_id = request.form.get('coach_id') or None # Optional

            # Validate required fields
            if not class_name or not level or not duration or not start_time or not capacity:
                flash("Please fill in all required fields.", "danger")
                return redirect(url_for('admin.manage_classes'))

            # Insert the new class with the selected coach
            try:
                cur.execute("""
                    INSERT INTO classes (class_name, description, level, duration, start_time, capacity, coach_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (class_name, description, level, duration, start_time, capacity, coach_id))
                mysql.connection.commit()
                flash("Class added successfully!", "success")
            except Exception as e:
                mysql.connection.rollback()
                flash("An error occurred while adding the class.", "danger")
                print("Error:", e)

        elif 'edit_class' in request.form:  # Editing an existing class
            class_id = request.form['class_id']
            class_name = request.form['class_name']
            description = request.form['description']
            level = request.form['level']
            duration = request.form['duration']
            start_time = request.form['start_time']
            capacity = request.form['capacity']
            coach_id = request.form.get('coach_id')  # Coach selection

            # Update the class with the new details
            try:
                cur.execute("""
                            UPDATE classes 
                            SET class_name = %s, description = %s, level = %s, 
                                duration = %s, start_time = %s, capacity = %s, coach_id = %s
                            WHERE class_id = %s
                        """, (class_name, description, level, duration, start_time, capacity, coach_id, class_id))
                mysql.connection.commit()
                flash("Class updated successfully!", "success")
            except Exception as e:
                mysql.connection.rollback()
                flash("An error occurred while updating the class.", "danger")
                print("Error:", e)

        # Registering a patient to a class
        elif 'register_patient' in request.form:
            patient_id = request.form['patient_id']
            class_id = request.form['class_id']

            # Check if the patient is already registered
            cur.execute("""
                    SELECT * FROM patient_classes WHERE patient_id = %s AND class_id = %s
                """, (patient_id, class_id))
            if cur.fetchone():
                flash("Patient is already registered for this class.", "info")
            else:
                #Insert registration into `patient_classes`
                try:
                    cur.execute("""
                        INSERT INTO patient_classes (patient_id, class_id)
                        VALUES (%s, %s)
                    """, (patient_id, class_id))
                    mysql.connection.commit()
                    flash("Patient successfully registered to the class!", "success")
                except Exception as e:
                    mysql.connection.rollback()
                    flash("An error occurred while registering the patient.", "danger")
                    print("Error:", e)
            #assign a coach to a class
        # Registering a patient to a class
        elif 'assign_coach' in request.form:
            coach_id = request.form['coach_id']
            class_id = request.form['class_id']

            # Verify the `coach_id` exists in the `coach` table
            cur.execute("SELECT coach_id FROM coach WHERE coach_id = %s", (coach_id,))
            coach_exists = cur.fetchone()

            if not coach_exists:
                flash("The selected coach does not exist.", "danger")
                return redirect(url_for('admin.manage_classes'))

            # Check if the class already has this coach assigned
            cur.execute("SELECT coach_id FROM classes WHERE class_id = %s", (class_id,))
            current_assignment = cur.fetchone()

            if current_assignment and current_assignment['coach_id'] == coach_id:
                flash("Coach is already assigned for this class.", "info")
            else:
                # Update the `coach_id` for the existing class
                try:
                    cur.execute("""
                                    UPDATE classes
                                    SET coach_id = %s
                                    WHERE class_id = %s
                                """, (coach_id, class_id))
                    mysql.connection.commit()
                    flash("Coach successfully assigned to the class!", "success")
                except Exception as e:
                    mysql.connection.rollback()
                    flash("An error occurred", "danger")
                    print("Error:", e)

    # Fetch all classes
    cur.execute("SELECT * FROM classes")
    classes = cur.fetchall()

    # Fetch all patients for the registration dropdown
    cur.execute("""
            SELECT patients.patient_id, users.username, users.email, patients.first_name, patients.dob, 
            patients.gender, patients.phone, patients.mobility_level
            FROM patients
            JOIN users ON patients.user_id = users.user_id
            WHERE users.role = 'patient'
            """)
    patients = cur.fetchall()

    # Fetch all users with the role 'coach' for the coach dropdown
    cur.execute("""
            SELECT users.user_id, users.username, users.email, coach.first_name, coach.last_name, 
            coach.specialization, coach.phone
            FROM users
            JOIN coach ON users.user_id = coach.user_id
            WHERE users.role = 'coach'
            """)
    coaches = cur.fetchall()

    # Fetch registered patients for each class
    class_registrations = {}
    for class_info in classes:
        cur.execute("""
            SELECT patients.first_name, patients.last_name 
            FROM patient_classes
            JOIN patients ON patient_classes.patient_id = patients.patient_id
            WHERE patient_classes.class_id = %s
        """, (class_info['class_id'],))
        class_registrations[class_info['class_id']] = cur.fetchall()

    cur.close()

    return render_template('classes.html', classes=classes, patients=patients,
                           class_registrations=class_registrations, coaches=coaches)

