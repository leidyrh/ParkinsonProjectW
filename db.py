import MySQLdb
from MySQLdb.cursors import DictCursor

def get_db_connection(app):
    """Function to get the MySQL database connection."""
    return MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB'],
        cursorclass=DictCursor
    )

