# create_user.py

from your_app import app, db
from your_app.models import User  # Adjust this if your User model is in another file
from werkzeug.security import generate_password_hash

def create_user():
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    hashed_password = generate_password_hash(password)

    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        print(f"User '{username}' created successfully.")

if __name__ == '__main__':
    create_user()

