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
                MAX_ADMINS = 5
                # # Ensure the new role is either 'patient' or 'coach' (not 'admin')
                # if new_role not in ['patient', 'coach']:
                #     flash('Only "patient" or "coach" roles can be assigned.', 'danger')
                #     return redirect(url_for('admin.admin_dashboard'))
                    # Ensure the new role is either 'patient' or 'coach' or check if adding 'admin'
                if new_role == 'admin':
                    # Count the number of existing admins
                    cur.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'")
                    admin_count = cur.fetchone()['admin_count']

                    if admin_count >= MAX_ADMINS:
                        flash(f'Cannot assign more than {MAX_ADMINS} admins.', 'danger')
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

@admin_bp.route('/edit_user', methods=['POST'])
def edit_user():
    if 'user_id' not in session:
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = request.form['user_id']
    new_username = request.form['username']
    new_password = request.form['password']

    # Validate new username and password (using your existing validation functions)
    if not is_valid_username(new_username):
        flash("Invalid username! It should be alphanumeric and between 3 to 15 characters.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    if not is_strong_password(new_password):
        flash("Password is too weak! It should be at least 8 characters long, contain a number, and a special character.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    # Hash the new password
    hashed_password = generate_password_hash(new_password)

    # Update the user's username and password in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET username = %s, password = %s WHERE user_id = %s", (new_username, hashed_password, user_id))
    mysql.connection.commit()

    flash('User information updated successfully!', 'success')
    return redirect(url_for('admin.admin_dashboard'))

