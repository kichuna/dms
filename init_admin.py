from app import app, db, User
from werkzeug.security import generate_password_hash

def init_admin():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            # Update admin password
            admin.password = generate_password_hash('admin', method='pbkdf2:sha256')
            admin.role = 'admin'
        else:
            # Create new admin user
            admin = User(
                username='admin',
                password=generate_password_hash('admin', method='pbkdf2:sha256'),
                role='admin'
            )
            db.session.add(admin)
        
        try:
            db.session.commit()
            print("Admin user created/updated successfully!")
            print("You can now login with:")
            print("Username: admin")
            print("Password: admin")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")

if __name__ == "__main__":
    init_admin() 