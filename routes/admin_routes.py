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

                # Generate a password hash
                # Hash the password before storing it
                hashed_pw = generate_password_hash(password)

                cur = mysql.connection.cursor()
                # Insert the new patient into the database
                cur.execute("INSERT INTO users (username, password,email, role) VALUES (%s, %s, %s,%s)",
                            (username, hashed_pw,email,role))
                mysql.connection.commit()

                flash('New patient created successfully!', 'success')

            elif action == 'assign_role':
                # Assign a new role to an existing user
                user_id = request.form['user_id']
                new_role = request.form['new_role']
                # Ensure the new role is either 'patient' or 'coach' (not 'admin')
                if new_role not in ['patient', 'coach']:
                    flash('Only "patient" or "coach" roles can be assigned.', 'danger')
                    return redirect(url_for('admin.admin_dashboard'))

                # Update the user's role in the database
                cur = mysql.connection.cursor()
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

@admin_bp.route('/create_patient', methods=['GET', 'POST'])
def create_patient():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('home'))  # Redirect to home if not admin

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Validate input using regular expressions
        if not is_valid_username(username):
            flash("Invalid username! It should be alphanumeric and between 3 to 15 characters.", "danger")
            return redirect(url_for('admin.create_patient'))

        if not is_valid_email(email):
            flash("Invalid email format!", "danger")
            return redirect(url_for('admin.create_patient'))

        if not is_strong_password(password):
            flash(
                "Password is too weak! It should be at least 8 characters long, contain a number, and a special character.",
                "danger")
            return redirect(url_for('admin.create_patient'))

        # Insert into users table (no password hashing, just plain text)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s)",
                    (username, password, 'patient', email))
        mysql.connection.commit()

        # Get user ID
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        # Insert into patients table
        cur.execute("INSERT INTO patients (user_id, name, age, gender) VALUES (%s, %s, %s, %s)",
                    (user[0], name, age, gender))
        mysql.connection.commit()

        flash('Patient created successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('create_patient.html')

@admin_bp.route('/assign_role/<int:user_id>', methods=['GET', 'POST'])
def assign_role(user_id):
    if 'user_id' not in session:
        flash('You must be logged in to assign roles.', 'warning')
        return redirect(url_for('auth.login'))
    # Get a cursor from the MySQL connection
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        new_role = request.form['role']  # Role can be 'patient', 'admin', etc.
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        mysql.connection.commit()
        cur.close()

        flash('Role successfully assigned!', 'success')
        return redirect(url_for('admin.admin_dashboard'))  # Redirect back to admin dashboard

    # Get user details for the admin to view before assigning a role
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    return render_template('assign_role.html', user=user)

# Additional route to handle user deletion
@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    mysql.connection.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.admin_dashboard'))
