import MySQLdb
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash
from app import mysql
from routes.auth_routes import is_valid_username, is_valid_email, is_strong_password


admin_classes_bp = Blueprint('admin_classes', __name__, url_prefix='/admin_classes')

@admin_classes_bp.route('/classes', methods=['GET', 'POST'])
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
                return redirect(url_for('admin_classes.manage_classes'))

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
        elif 'assign_coach' in request.form:
            coach_id = request.form['coach_id']
            class_id = request.form['class_id']

            # Verify the `coach_id` exists in the `coach` table
            cur.execute("SELECT coach_id FROM coach WHERE coach_id = %s", (coach_id,))
            coach_exists = cur.fetchone()

            if not coach_exists:
                flash("The selected coach does not exist.", "danger")
                return redirect(url_for('admin_classes.manage_classes'))

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
            SELECT users.user_id AS coach_id, users.username, users.email, coach.first_name, coach.last_name, 
            coach.specialization, coach.phone
            FROM users
            JOIN coach ON users.user_id = coach.coach_id
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


@admin_classes_bp.route('/edit_class/<int:class_id>', methods=['GET', 'POST'])
def edit_class(class_id):
    # Ensure the user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("You must be an admin to access this page.", "warning")
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        # Get updated class data from the form
        class_name = request.form['class_name']
        description = request.form['description']
        level = request.form['level']
        duration = request.form['duration']
        start_time = request.form['start_time']
        capacity = request.form['capacity']
        coach_id = request.form.get('coach_id') or None  # Optional

        try:
            # Update the class details in the database
            cur.execute("""
                UPDATE classes
                SET class_name = %s, description = %s, level = %s, duration = %s, start_time = %s, capacity = %s, coach_id = %s
                WHERE class_id = %s
            """, (class_name, description, level, duration, start_time, capacity, coach_id, class_id))
            mysql.connection.commit()
            flash("Class updated successfully!", "success")
            return redirect(url_for('admin.manage_classes'))
        except Exception as e:
            mysql.connection.rollback()
            flash("An error occurred while updating the class.", "danger")
            print("Error:", e)

    # Fetch the existing class details for the form
    cur.execute("SELECT * FROM classes WHERE class_id = %s", (class_id,))
    class_details = cur.fetchone()
    cur.close()

    return render_template('classes.html', class_details=class_details)


@admin_classes_bp.route('/delete_class/<int:class_id>', methods=['POST'])
def delete_class(class_id):
    # Ensure the user is an admin
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("You must be an admin to access this page.", "warning")
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    try:
        # Delete the class from the database
        cur.execute("DELETE FROM classes WHERE class_id = %s", (class_id,))
        mysql.connection.commit()
        flash("Class deleted successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash("An error occurred while deleting the class.", "danger")
        print("Error:", e)
    finally:
        cur.close()

    return redirect(url_for('admin.manage_classes'))

