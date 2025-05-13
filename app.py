from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import logging
import csv
from io import StringIO

logging.basicConfig(filename='app.log', level=logging.ERROR)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'children_db'

mysql = MySQL(app)

# Uploads directory
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('data_display'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user_data = cur.fetchone()
        except Exception as e:
            flash(f"Error logging in: {e}", 'danger')
            user_data = None
        finally:
            cur.close()

        if user_data:
            user = User(user_data[0], user_data[1], user_data[2], user_data[3])
            login_user(user)
            return redirect(url_for('data_display'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')


@app.route('/import_csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    if current_user.role != 'admin':
        flash('You do not have permission to access the import wizard.', 'danger')
        return redirect(url_for('data_display'))

    if request.method == 'POST':
        file = request.files['csv_file']
        
        if not file or file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('import_csv'))

        if file and file.filename.endswith('.csv'):
            try:
                # Read the CSV file
                file_content = file.stream.read().decode('utf-8')
                csv_reader = csv.reader(StringIO(file_content))

                # Skip header row
                next(csv_reader)

                # Loop through the rows and insert data into the database
                cur = mysql.connection.cursor()
                for row in csv_reader:
                    name, date_of_birth, gender, guardian_name, guardian_contact, address, date_of_admission, nature_of_case, status = row
                    cur.execute("""
                        INSERT INTO children (name, date_of_birth, gender, guardian_name, guardian_contact, address, date_of_admission, nature_of_case, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, date_of_birth, gender, guardian_name, guardian_contact, address, date_of_admission, nature_of_case, status))
                
                mysql.connection.commit()
                flash('CSV data imported successfully!', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash(f"Error importing CSV data: {e}", 'danger')
            finally:
                cur.close()

            return redirect(url_for('data_display'))
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')

    return render_template('import_csv.html')  # Ensure you create this template for file upload form.







@app.route('/data_entry', methods=['GET', 'POST'])
@login_required
def data_entry():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('data_display'))

    if request.method == 'POST':
        name = request.form['name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        guardian_name = request.form['guardian_name']
        guardian_contact = request.form['guardian_contact']
        address = request.form['address']
        date_of_admission = request.form['date_of_admission']
        nature_of_case = request.form['nature_of_case']
        status = request.form['status']
        photo = request.files.get('photo')

        filename = None
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO children 
                (name, date_of_birth, gender, guardian_name, guardian_contact, address, date_of_admission, nature_of_case, status, photo) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, 
                (name, date_of_birth, gender, guardian_name, guardian_contact, address, date_of_admission, nature_of_case, status, filename)
            )
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error inserting data: {e}", 'danger')
        finally:
            cur.close()

        return redirect(url_for('data_display'))

    return render_template('data_entry.html')

@app.route('/data_display', methods=['GET'])
@login_required
def data_display():
    search_query = request.args.get('search', '').strip()

    cur = mysql.connection.cursor()
    try:
        if search_query:
            cur.execute("SELECT * FROM children WHERE name LIKE %s", ('%' + search_query + '%',))
        else:
            cur.execute("SELECT * FROM children")
        children = cur.fetchall()
    except Exception as e:
        flash(f"Error fetching data: {e}", 'danger')
        children = []
    finally:
        cur.close()

    return render_template('data_display.html', children=children, search_query=search_query)

@app.route('/child_detail/<int:child_id>')
@login_required
def child_detail(child_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM children WHERE id = %s", (child_id,))
        child = cur.fetchone()
    except Exception as e:
        flash(f"Error fetching child detail: {e}", 'danger')
        child = None
    finally:
        cur.close()
    return render_template('child_detail.html', child=child)

@app.route('/edit_child/<int:child_id>', methods=['GET', 'POST'])
@login_required
def edit_child(child_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM children WHERE id = %s", (child_id,))
    child = cur.fetchone()
    cur.close()

    if not child:
        flash('Child not found', 'danger')
        return redirect(url_for('data_display'))

    if request.method == 'POST':
        name = request.form['name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        guardian_name = request.form['guardian_name']
        guardian_contact = request.form['guardian_contact']
        address = request.form['address']
        date_of_admission = request.form['date_of_admission']
        nature_of_case = request.form['nature_of_case']
        status = request.form['status']
        photo = request.files.get('photo')

        filename = child[9]  # existing photo filename
        if photo and photo.filename != '':
            # Remove old photo if it exists
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            # Save new photo
            filename = secure_filename(photo.filename)
            new_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(new_path)

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                UPDATE children 
                SET name=%s, date_of_birth=%s, gender=%s, guardian_name=%s, guardian_contact=%s, address=%s, 
                    date_of_admission=%s, nature_of_case=%s, status=%s, photo=%s 
                WHERE id=%s
                """,
                (name, date_of_birth, gender, guardian_name, guardian_contact, address,
                 date_of_admission, nature_of_case, status, filename, child_id)
            )
            mysql.connection.commit()
            flash('Child record updated successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error updating child: {e}", 'danger')
        finally:
            cur.close()

        return redirect(url_for('data_display'))

    return render_template('edit_child.html', child=child)

@app.route('/delete_child/<int:child_id>', methods=['POST'])
@login_required
def delete_child(child_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete records.', 'danger')
        return redirect(url_for('data_display'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT photo FROM children WHERE id = %s", (child_id,))
        result = cur.fetchone()
        if result and result[0]:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], result[0])
            if os.path.exists(photo_path):
                os.remove(photo_path)

        cur.execute("DELETE FROM children WHERE id = %s", (child_id,))
        mysql.connection.commit()
        flash('Child record deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting child: {e}", 'danger')
    finally:
        cur.close()

    return redirect(url_for('data_display'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
