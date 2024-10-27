from flask import Blueprint, render_template, session, redirect, url_for, request
from flask_mysqldb import MySQL

chat_bp = Blueprint('chat', __name__)
mysql = MySQL()


# Chat Room Route
@chat_bp.route('/chat/<int:receiver_id>')
def chat(receiver_id):
    if 'logged_in' in session:
        # Get the current user's ID
        sender_id = session['user_id']

        # Retrieve messages for the conversation between sender and receiver
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT m.id, m.message, m.timestamp, 
                   u1.username AS sender_username, 
                   u2.username AS receiver_username 
            FROM messages m
            JOIN users u1 ON m.sender_id = u1.id
            JOIN users u2 ON m.receiver_id = u2.id
            WHERE (m.sender_id = %s AND m.receiver_id = %s) 
               OR (m.sender_id = %s AND m.receiver_id = %s)
            ORDER BY m.timestamp ASC
        """, (sender_id, receiver_id, receiver_id, sender_id))

        messages = cur.fetchall()  # Fetch all messages for the conversation
        cur.close()

        # Pass messages and receiver info to the chat room template
        return render_template('chat_room.html', messages=messages, receiver_id=receiver_id)
    else:
        return redirect(url_for('login'))  # Redirect to login if not authenticated


# Route to Send Message
@chat_bp.route('/send_message', methods=['POST'])
def send_message():
    if 'logged_in' in session:
        message = request.form['message']
        receiver_id = request.form['receiver_id']
        sender_id = session['user_id']

        # Store the message in the database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO messages (sender_id, receiver_id, message) 
            VALUES (%s, %s, %s)
        """, (sender_id, receiver_id, message))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('chat.chat', receiver_id=receiver_id))  # Redirect back to chat room
    else:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

