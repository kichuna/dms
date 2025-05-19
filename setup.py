import os
import sys
import shutil
import subprocess
from app import app, db, User
from werkzeug.security import generate_password_hash

def initialize_database():
    print("Initializing database...")
    instance_path = os.path.join(os.getcwd(), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    db_path = os.path.join(instance_path, 'children.db')
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")

def create_executable():
    print("Creating executable...")
    
    # Initialize database first
    initialize_database()
    
    # Create run.py
    run_py_content = """from app import app

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)
"""
    with open('run.py', 'w') as f:
        f.write(run_py_content)
    
    # Create start_app.bat
    bat_content = """@echo off
echo Starting Children Management System...
echo Please wait while the application loads...
echo.
echo Default login credentials:
echo Username: admin
echo Password: admin123
echo.
start http://127.0.0.1:5000
cd dist
run.exe
pause
"""
    with open('start_app.bat', 'w') as f:
        f.write(bat_content)
    
    # Run PyInstaller
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--add-data', 'templates;templates',
        '--add-data', 'static;static',
        '--add-data', 'instance;instance',  # Include the database
        '--hidden-import', 'flask',
        '--hidden-import', 'flask_login',
        '--hidden-import', 'flask_sqlalchemy',
        'run.py'
    ])
    
    # Create distribution folder
    if not os.path.exists('distribution'):
        os.makedirs('distribution')
    
    # Copy necessary files to distribution folder
    shutil.copy('dist/run.exe', 'distribution/')
    shutil.copy('start_app.bat', 'distribution/')
    
    # Copy instance folder with database
    if os.path.exists('instance'):
        shutil.copytree('instance', 'distribution/instance', dirs_exist_ok=True)
    
    print("\nExecutable created successfully!")
    print("The executable and necessary files are in the 'distribution' folder.")
    print("\nTo run the application:")
    print("1. Copy the 'distribution' folder to your desired location")
    print("2. Run 'start_app.bat' inside the distribution folder")
    print("\nDefault login credentials:")
    print("Username: admin")
    print("Password: admin123")

if __name__ == '__main__':
    create_executable() 