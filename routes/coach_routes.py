from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_mysqldb import MySQL

coach_bp = Blueprint('coach', __name__, url_prefix='/coach')
mysql = MySQL()

# Coach Dashboard Route
@coach_bp.route('/dashboard')
def coach_dashboard():
    """Displays the patient's dashboard."""
    if 'role' not in session or session['role'] != 'coach':
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated as patient

    user_id = session.get('user_id')

    # Get the patient's information from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM coach WHERE user_id = %s", (user_id,))
    coach = cur.fetchone()

    if not coach:
        flash("Coach not found!", "danger")
        return redirect(url_for('home'))

    return render_template('coach_dashboard.html', patient=coach)

# Optional: Route for Logging Out
@coach_bp.route('/logout')
def logout():
    session.clear()  # Clear the session data
    return redirect(url_for('login'))  # Redirect to login page
