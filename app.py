from flask import Flask, redirect, url_for
from flask_mysqldb import MySQL
from config import DevelopmentConfig  # or choose a different environment (e.g., ProductionConfig)


mysql = MySQL()

def create_app():
    app = Flask(__name__)
    # Load configuration from the config.py file
    app.config.from_object(DevelopmentConfig)  # You can change this to use ProductionConfig or TestingConfig'

    # Initialize MySQL with the Flask app
    mysql.init_app(app)


    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.patient_routes import patient_bp
    from routes.coach_routes import coach_bp
    from routes.chat_routes import chat_bp
    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(coach_bp, url_prefix='/coach')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    # Home Route (Landing Page)
    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))

    return app

# @app.route('/')
# def home():
#     return render_template('login.html')
#
#
# @app.route('/login', methods=['POST'])
# def login():
#     username = request.form['username']
#     password = request.form['password']
#
#     print(f"Attempting to log in: {username}")  # Debug line
#
#     if username in users and users[username] == password:
#         print(f"Login successful for: {username}")  # Debug line
#         return redirect(url_for('chat', username=username))  # Redirect to the chat page
#     else:
#         flash('Invalid username or password!')
#         print(f"Invalid credentials for: {username}")  # Debug line
#         return redirect(url_for('home'))
#
#
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#
#         if username in users:
#             flash('Username already exists! Please choose a different one.')
#             return redirect(url_for('register'))
#
#         users[username] = password
#         flash('Registration successful! You can now log in.')
#         return redirect(url_for('home'))
#
#     return render_template('register.html')
#
#
# @app.route('/chat/<username>')
# def chat(username):
#     return render_template('chat.html', username=username)  # Render the chat page



if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
