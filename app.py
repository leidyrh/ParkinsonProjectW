import os
from datetime import timedelta

from flask import Flask,   redirect, url_for
from flask_mysqldb import MySQL
from config import DevelopmentConfig  # or choose a different environment (e.g., ProductionConfig)

mysql = MySQL()

# Initialize MySQL


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
    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(coach_bp, url_prefix='/coach')

# Home Route (Landing Page)
    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

