import mysql.connector
import os
from app import app, db, User
from werkzeug.security import generate_password_hash

def create_database():
    # MySQL connection parameters
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'children_db')

    # Create database if it doesn't exist
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    cursor = connection.cursor()

    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}")
        print(f"Database '{MYSQL_DATABASE}' created successfully!")
    except mysql.connector.Error as err:
        print(f"Error creating database: {err}")
        return False
    finally:
        cursor.close()
        connection.close()

    return True

def initialize_database():
    print("Initializing database...")
    
    # Create database first
    if not create_database():
        return

    # Create tables and admin user
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            # Create admin user if not exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    password=generate_password_hash('admin123', method='pbkdf2:sha256'),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
                print("Default login credentials:")
                print("Username: admin")
                print("Password: admin123")
            else:
                print("Admin user already exists!")
                
            print("Database initialized successfully!")
        except Exception as e:
            print(f"Error initializing database: {e}")

if __name__ == '__main__':
    initialize_database() 