from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import logging
import csv
from io import StringIO
from datetime import datetime, timedelta

logging.basicConfig(filename='app.log', level=logging.ERROR)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Database Configuration
if os.environ.get('RENDER'):
    # Production database URL from Render
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
else:
    # Local SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'dms.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Uploads directory
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Children(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    guardian_name = db.Column(db.String(100), nullable=False)
    guardian_contact = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    date_of_admission = db.Column(db.Date, nullable=False)
    nature_of_case = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(200))

class EducationSupportIndicators(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrolled_in_high_school = db.Column(db.Integer, default=0)
    enrolled_in_college = db.Column(db.Integer, default=0)
    continued_scholarship_support = db.Column(db.Integer, default=0)
    supported_with_transport = db.Column(db.Integer, default=0)
    supported_with_upkeep = db.Column(db.Integer, default=0)
    supported_with_scholastic_materials = db.Column(db.Integer, default=0)
    supported_with_pocket_money = db.Column(db.Integer, default=0)
    supported_with_tuition = db.Column(db.Integer, default=0)
    date_column = db.Column(db.Date, default=datetime.utcnow)

class FamilySupportProgramIndicators(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    financial_support = db.Column(db.Integer, default=0)
    housing_support = db.Column(db.Integer, default=0)
    healthcare_support = db.Column(db.Integer, default=0)
    food_support = db.Column(db.Integer, default=0)
    educational_support = db.Column(db.Integer, default=0)
    employment_support = db.Column(db.Integer, default=0)
    emotional_support = db.Column(db.Integer, default=0)
    legal_support = db.Column(db.Integer, default=0)
    date_column = db.Column(db.Date, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

        try:
            user = User.query.filter_by(username=username, password=password).first()
            if user:
                login_user(user)
                return redirect(url_for('data_display'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            flash(f"Error logging in: {e}", 'danger')

    return render_template('login.html')

@app.route('/help')
def help():
    return render_template('help.html')

def parse_date(date_str):
    """Try parsing date string in multiple formats."""
    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Date '{date_str}' does not match any of the supported formats: YYYY-MM-DD, M/D/YYYY, D/M/YYYY")

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
                file_content = file.stream.read().decode('utf-8')
                csv_reader = csv.reader(StringIO(file_content))
                next(csv_reader)  # Skip header

                for row in csv_reader:
                    try:
                        child = Children(
                            name=row[0],
                            date_of_birth=parse_date(row[1]),
                            gender=row[2],
                            guardian_name=row[3],
                            guardian_contact=row[4],
                            address=row[5],
                            date_of_admission=parse_date(row[6]),
                            nature_of_case=row[7],
                            status=row[8]
                        )
                        db.session.add(child)
                    except ValueError as e:
                        db.session.rollback()
                        flash(f"Error in row for {row[0]}: {str(e)}", 'danger')
                        return redirect(url_for('import_csv'))
                        
                db.session.commit()
                flash('CSV data imported successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f"Error importing CSV data: {str(e)}", 'danger')

            return redirect(url_for('data_display'))
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')

    return render_template('import_csv.html')

@app.route('/data_manager', methods=['GET', 'POST'])
@login_required
def data_manager():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('data_display'))

    if request.method == 'POST':
        try:
            indicator = EducationSupportIndicators(
                enrolled_in_high_school=int(request.form.get('enrolled_in_high_school')),
                enrolled_in_college=int(request.form.get('enrolled_in_college')),
                continued_scholarship_support=int(request.form.get('continued_scholarship_support')),
                supported_with_transport=int(request.form.get('supported_with_transport')),
                supported_with_upkeep=int(request.form.get('supported_with_upkeep')),
                supported_with_scholastic_materials=int(request.form.get('supported_with_scholastic_materials')),
                supported_with_pocket_money=int(request.form.get('supported_with_pocket_money')),
                supported_with_tuition=int(request.form.get('supported_with_tuition'))
            )
            db.session.add(indicator)
            db.session.commit()
            flash('Education support data submitted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error submitting data: {e}", 'danger')

        return redirect(url_for('data_manager'))

    return render_template('data_manager.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    dashboard_data = {}

    # Get the selected filter period from the form
    filter_period = request.form.get('filter-period', 'this-month')
    start_date = None
    end_date = None

    # Date filter logic
    if filter_period == 'this-month':
        start_date = datetime.now().replace(day=1).date()
        end_date = datetime.now().date()
    elif filter_period == 'last-3-months':
        end_date = datetime.now().date()
        start_date = (datetime.now() - timedelta(days=90)).date()
    elif filter_period == 'this-year':
        start_date = datetime.now().replace(month=1, day=1).date()
        end_date = datetime.now().date()
    elif filter_period == 'custom':
        start_date_str = request.form.get('start-date', '')
        end_date_str = request.form.get('end-date', '')

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Invalid custom date format. Please select valid dates.", "danger")
                return redirect(request.url)
        else:
            flash("Please provide both a start and end date for the custom range.", "danger")
            return redirect(request.url)

    # Education Support Indicators
    education_data = EducationSupportIndicators.query.filter(
        EducationSupportIndicators.date_column.between(start_date, end_date)
    ).all()

    dashboard_data.update({
        'total_enrolled_in_high_school': sum(1 for e in education_data if e.enrolled_in_high_school),
        'total_enrolled_in_college': sum(1 for e in education_data if e.enrolled_in_college),
        'total_continued_scholarship_support': sum(1 for e in education_data if e.continued_scholarship_support),
        'total_supported_with_transport': sum(1 for e in education_data if e.supported_with_transport),
        'total_supported_with_upkeep': sum(1 for e in education_data if e.supported_with_upkeep),
        'total_supported_with_scholastic_materials': sum(1 for e in education_data if e.supported_with_scholastic_materials),
        'total_supported_with_pocket_money': sum(1 for e in education_data if e.supported_with_pocket_money),
        'total_supported_with_tuition': sum(1 for e in education_data if e.supported_with_tuition)
    })

    # Family Support Indicators
    family_data = FamilySupportProgramIndicators.query.filter(
        FamilySupportProgramIndicators.date_column.between(start_date, end_date)
    ).all()

    dashboard_data.update({
        'total_financial_support': sum(1 for f in family_data if f.financial_support),
        'total_housing_support': sum(1 for f in family_data if f.housing_support),
        'total_healthcare_support': sum(1 for f in family_data if f.healthcare_support),
        'total_food_support': sum(1 for f in family_data if f.food_support),
        'total_educational_support': sum(1 for f in family_data if f.educational_support),
        'total_employment_support': sum(1 for f in family_data if f.employment_support),
        'total_emotional_support': sum(1 for f in family_data if f.emotional_support),
        'total_legal_support': sum(1 for f in family_data if f.legal_support)
    })

    return render_template('dashboard.html', **dashboard_data)

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    labels = []
    values = []

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        filter_period = request.form.get('period')
        start_date = None
        end_date = None

        # Handle date range based on filter
        if filter_period == 'this-month':
            start_date = datetime.now().replace(day=1).date()
            end_date = datetime.now().date()
        elif filter_period == 'last-3-months':
            end_date = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=90)).date()
        elif filter_period == 'this-year':
            start_date = datetime.now().replace(month=1, day=1).date()
            end_date = datetime.now().date()
        elif filter_period == 'custom':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Invalid custom date format. Please use YYYY-MM-DD.", "danger")
                return redirect(request.url)

        if report_type == 'education':
            labels = [
                'High School', 'College', 'Scholarship', 'Transport',
                'Upkeep', 'Materials', 'Pocket Money', 'Tuition'
            ]
            education_data = EducationSupportIndicators.query.filter(
                EducationSupportIndicators.date_column.between(start_date, end_date)
            ).all()
            values = [
                sum(1 for e in education_data if e.enrolled_in_high_school),
                sum(1 for e in education_data if e.enrolled_in_college),
                sum(1 for e in education_data if e.continued_scholarship_support),
                sum(1 for e in education_data if e.supported_with_transport),
                sum(1 for e in education_data if e.supported_with_upkeep),
                sum(1 for e in education_data if e.supported_with_scholastic_materials),
                sum(1 for e in education_data if e.supported_with_pocket_money),
                sum(1 for e in education_data if e.supported_with_tuition)
            ]

        elif report_type == 'family':
            labels = [
                'Financial', 'Housing', 'Healthcare', 'Food',
                'Education', 'Employment', 'Emotional', 'Legal'
            ]
            family_data = FamilySupportProgramIndicators.query.filter(
                FamilySupportProgramIndicators.date_column.between(start_date, end_date)
            ).all()
            values = [
                sum(1 for f in family_data if f.financial_support),
                sum(1 for f in family_data if f.housing_support),
                sum(1 for f in family_data if f.healthcare_support),
                sum(1 for f in family_data if f.food_support),
                sum(1 for f in family_data if f.educational_support),
                sum(1 for f in family_data if f.employment_support),
                sum(1 for f in family_data if f.emotional_support),
                sum(1 for f in family_data if f.legal_support)
            ]

    return render_template('reports.html', labels=labels, values=values)

@app.route('/add_family_program_data', methods=['GET', 'POST'])
@login_required
def add_family_program_data():
    if request.method == 'POST':
        try:
            indicator = FamilySupportProgramIndicators(
                financial_support=int(request.form.get('financial_support')),
                housing_support=int(request.form.get('housing_support')),
                healthcare_support=int(request.form.get('healthcare_support')),
                food_support=int(request.form.get('food_support')),
                educational_support=int(request.form.get('educational_support')),
                employment_support=int(request.form.get('employment_support')),
                emotional_support=int(request.form.get('emotional_support')),
                legal_support=int(request.form.get('legal_support')),
                date_column=datetime.now().date()
            )
            db.session.add(indicator)
            db.session.commit()
            flash('Family program data added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding family program data: {e}', 'danger')
        return redirect(url_for('add_family_program_data'))

    return render_template('add_family_program_data.html')

@app.route('/data_entry', methods=['GET', 'POST'])
@login_required
def data_entry():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('data_display'))

    if request.method == 'POST':
        try:
            photo = request.files.get('photo')
            filename = None
            if photo and photo.filename != '':
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            child = Children(
                name=request.form['name'],
                date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date(),
                gender=request.form['gender'],
                guardian_name=request.form['guardian_name'],
                guardian_contact=request.form['guardian_contact'],
                address=request.form['address'],
                date_of_admission=datetime.strptime(request.form['date_of_admission'], '%Y-%m-%d').date(),
                nature_of_case=request.form['nature_of_case'],
                status=request.form['status'],
                photo=filename
            )
            db.session.add(child)
            db.session.commit()
            flash('Child record added successfully!', 'success')
            return redirect(url_for('data_display'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding child record: {e}', 'danger')

    return render_template('data_entry.html')

@app.route('/data_display')
@login_required
def data_display():
    search_query = request.args.get('search', '').strip()
    if search_query:
        children = Children.query.filter(Children.name.like(f'%{search_query}%')).all()
    else:
        children = Children.query.all()
    return render_template('data_display.html', children=children, search_query=search_query)

@app.route('/child_detail/<int:child_id>')
@login_required
def child_detail(child_id):
    child = Children.query.get_or_404(child_id)
    return render_template('child_detail.html', child=child)

@app.route('/edit_child/<int:child_id>', methods=['GET', 'POST'])
@login_required
def edit_child(child_id):
    child = Children.query.get_or_404(child_id)

    if request.method == 'POST':
        try:
            photo = request.files.get('photo')
            if photo and photo.filename != '':
                if child.photo:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], child.photo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                child.photo = filename

            child.name = request.form['name']
            child.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()
            child.gender = request.form['gender']
            child.guardian_name = request.form['guardian_name']
            child.guardian_contact = request.form['guardian_contact']
            child.address = request.form['address']
            child.date_of_admission = datetime.strptime(request.form['date_of_admission'], '%Y-%m-%d').date()
            child.nature_of_case = request.form['nature_of_case']
            child.status = request.form['status']

            db.session.commit()
            flash('Child record updated successfully!', 'success')
            return redirect(url_for('data_display'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating child record: {e}', 'danger')

    return render_template('edit_child.html', child=child)

@app.route('/delete_child/<int:child_id>', methods=['POST'])
@login_required
def delete_child(child_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete records.', 'danger')
        return redirect(url_for('data_display'))

    child = Children.query.get_or_404(child_id)
    try:
        if child.photo:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], child.photo)
            if os.path.exists(photo_path):
                os.remove(photo_path)

        db.session.delete(child)
        db.session.commit()
        flash('Child record deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting child record: {e}', 'danger')

    return redirect(url_for('data_display'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/indicators')
@login_required
def indicators():
    education_indicators = EducationSupportIndicators.query.order_by(EducationSupportIndicators.date_column.desc()).all()
    family_indicators = FamilySupportProgramIndicators.query.order_by(FamilySupportProgramIndicators.date_column.desc()).all()
    return render_template('indicators_display.html', 
                         education_indicators=education_indicators,
                         family_indicators=family_indicators)

@app.route('/update_indicator', methods=['POST'])
@login_required
def update_indicator():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'})

    try:
        data = request.get_json()
        indicator_id = data['id']
        program = data['program']
        values = data['values']

        if program == 'education':
            indicator = EducationSupportIndicators.query.get_or_404(indicator_id)
            indicator.enrolled_in_high_school = values[0]
            indicator.enrolled_in_college = values[1]
            indicator.continued_scholarship_support = values[2]
            indicator.supported_with_transport = values[3]
            indicator.supported_with_upkeep = values[4]
            indicator.supported_with_scholastic_materials = values[5]
            indicator.supported_with_pocket_money = values[6]
            indicator.supported_with_tuition = values[7]
        else:
            indicator = FamilySupportProgramIndicators.query.get_or_404(indicator_id)
            indicator.financial_support = values[0]
            indicator.housing_support = values[1]
            indicator.healthcare_support = values[2]
            indicator.food_support = values[3]
            indicator.educational_support = values[4]
            indicator.employment_support = values[5]
            indicator.emotional_support = values[6]
            indicator.legal_support = values[7]

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_indicator/<program>/<int:indicator_id>', methods=['POST'])
@login_required
def delete_indicator(program, indicator_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'})

    try:
        if program == 'education':
            indicator = EducationSupportIndicators.query.get_or_404(indicator_id)
        else:
            indicator = FamilySupportProgramIndicators.query.get_or_404(indicator_id)

        db.session.delete(indicator)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
