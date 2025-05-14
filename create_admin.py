import sqlite3

# Connect to the database
conn = sqlite3.connect('dms.db')
cursor = conn.cursor()

# List all tables
print("Tables in database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

# View contents of a specific table
table_name = 'education_support_indicators'  # or 'family_support_program_indicators'
print(f"\nData in table: {table_name}")
cursor.execute(f"SELECT * FROM {table_name}")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
