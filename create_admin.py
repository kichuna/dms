import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('dms.db')
cursor = conn.cursor()

username = input("Enter username: ")
password = input("Enter password: ")
role = input("Enter role (admin or user): ")

hashed_password = generate_password_hash(password)

try:
    cursor.execute("INSERT INTO user (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
    conn.commit()
    print("User created successfully!")
except sqlite3.IntegrityError as e:
    print(f"Error: {e}")

conn.close()
