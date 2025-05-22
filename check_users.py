from app import app, db, User
from werkzeug.security import generate_password_hash

def check_and_update_users():
    with app.app_context():
        # List all users
        users = User.query.all()
        print("\nExisting users:")
        for user in users:
            print(f"Username: {user.username}, Role: {user.role}")
        
        # Update admin password
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.password = generate_password_hash('admin', method='pbkdf2:sha256')
            try:
                db.session.commit()
                print("\nAdmin password has been updated!")
                print("New login credentials:")
                print("Username: admin")
                print("Password: admin")
            except Exception as e:
                db.session.rollback()
                print(f"\nError updating password: {e}")
        else:
            print("\nNo admin user found in the database.")

if __name__ == "__main__":
    check_and_update_users() 