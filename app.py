from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
import os
import logging
import csv
from io import StringIO
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import random
import string
import json
import traceback
from logging.handlers import RotatingFileHandler
from functools import wraps
from utils.config_manager import config_manager
from math import ceil

# Create a logger at module level
logger = logging.getLogger('dms')
logger.setLevel(logging.ERROR)

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'

# Absolute path to current directory
basedir = os.path.abspath(os.path.dirname(__file__))

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_manager._config)
    
    # Set SQLite database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'dms.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Set secret key for CSRF protection
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Configure logging
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set up file handler for local logging
    log_file = os.path.join(logs_dir, 'dms.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

    # Add error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        logger.error(f'Page not found: {request.url}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Server Error: {error}')
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf = CSRFProtect(app)

    return app

# Create the application instance
app = create_app()

# Create all database tables
with app.app_context():
    db.create_all()

# Uploads directory
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Add custom date filter
@app.template_filter('date')
def format_date(value, format='%Y-%m-%d'):
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    return value.strftime(format)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

    def __repr__(self):
        return f'<User {self.username}>'

class ProgramDefinition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    fields = db.relationship('ProgramField', backref='program', lazy=True, cascade='all, delete-orphan')
    data = db.relationship('ProgramData', backref='program', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Program {self.name}>'

class ProgramField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program_definition.id'), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)
    field_label = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(20), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    validation_rules = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<ProgramField {self.field_name}>'

class ProgramData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('program_definition.id'), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<ProgramData {self.id}>'

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

    def __repr__(self):
        return f'<Children {self.name}>'

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

    def __repr__(self):
        return f'<EducationSupportIndicators {self.id}>'

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

    def __repr__(self):
        return f'<FamilySupportProgramIndicators {self.id}>'

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_message = str(e)
            error_details = traceback.format_exc()
            
            # Log the error
            logger.error(f"Error in {f.__name__}: {error_message}\n{error_details}")
            
            # Flash error message to user
            flash(f'An error occurred: {error_message}', 'danger')
            
            # Return appropriate response
            if request.is_json:
                return jsonify({'error': error_message}), 500
            return redirect(url_for('index'))
    return decorated_function

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
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('data_display'))
            else:
                flash('Invalid username or password', 'danger')
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
@login_required
def dashboard():
    # Default filter values
    filter_period = request.form.get('filter-period', 'this-month')
    start_date = None
    end_date = None

    today = datetime.today()

    if filter_period == 'this-month':
        start_date = today.replace(day=1)
        end_date = today
    elif filter_period == 'last-3-months':
        start_date = today - timedelta(days=90)
        end_date = today
    elif filter_period == 'this-year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif filter_period == 'custom':
        start_date = request.form.get('start-date')
        end_date = request.form.get('end-date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

    # Build query filters
    education_query = EducationSupportIndicators.query
    family_query = FamilySupportProgramIndicators.query

    if start_date and end_date:
        education_query = education_query.filter(EducationSupportIndicators.date_column.between(start_date, end_date))
        family_query = family_query.filter(FamilySupportProgramIndicators.date_column.between(start_date, end_date))

    # Aggregate education support data
    education_sums = {
        'total_enrolled_in_high_school': 0,
        'total_enrolled_in_college': 0,
        'total_continued_scholarship_support': 0,
        'total_supported_with_transport': 0,
        'total_supported_with_upkeep': 0,
        'total_supported_with_scholastic_materials': 0,
        'total_supported_with_pocket_money': 0,
        'total_supported_with_tuition': 0,
    }

    for record in education_query.all():
        education_sums['total_enrolled_in_high_school'] += record.enrolled_in_high_school or 0
        education_sums['total_enrolled_in_college'] += record.enrolled_in_college or 0
        education_sums['total_continued_scholarship_support'] += record.continued_scholarship_support or 0
        education_sums['total_supported_with_transport'] += record.supported_with_transport or 0
        education_sums['total_supported_with_upkeep'] += record.supported_with_upkeep or 0
        education_sums['total_supported_with_scholastic_materials'] += record.supported_with_scholastic_materials or 0
        education_sums['total_supported_with_pocket_money'] += record.supported_with_pocket_money or 0
        education_sums['total_supported_with_tuition'] += record.supported_with_tuition or 0

    # Aggregate family support data
    family_sums = {
        'total_financial_support': 0,
        'total_housing_support': 0,
        'total_healthcare_support': 0,
        'total_food_support': 0,
        'total_educational_support': 0,
        'total_employment_support': 0,
        'total_emotional_support': 0,
        'total_legal_support': 0,
    }

    for record in family_query.all():
        family_sums['total_financial_support'] += record.financial_support or 0
        family_sums['total_housing_support'] += record.housing_support or 0
        family_sums['total_healthcare_support'] += record.healthcare_support or 0
        family_sums['total_food_support'] += record.food_support or 0
        family_sums['total_educational_support'] += record.educational_support or 0
        family_sums['total_employment_support'] += record.employment_support or 0
        family_sums['total_emotional_support'] += record.emotional_support or 0
        family_sums['total_legal_support'] += record.legal_support or 0

    # Get custom programs data
    custom_programs = ProgramDefinition.query.all()
    custom_programs_data = {}
    
    for program in custom_programs:
        program_data = ProgramData.query.filter(
            ProgramData.program_id == program.id
        )
        if start_date and end_date:
            program_data = program_data.filter(
                ProgramData.created_at.between(start_date, end_date)
            )
        
        # Calculate sums for numeric fields
        sums = {}
        for field in program.fields:
            if field.field_type == 'number':
                sums[field.field_name] = sum(
                    float(entry.data.get(field.field_name, 0) or 0)
                    for entry in program_data.all()
                )
        
        custom_programs_data[program.id] = {
            'name': program.name,
            'sums': sums
        }

    # Pass all values to template
    return render_template("dashboard.html",
        filter_period=filter_period,
        start_date=start_date.strftime('%Y-%m-%d') if start_date else '',
        end_date=end_date.strftime('%Y-%m-%d') if end_date else '',
        **education_sums,
        **family_sums,
        custom_programs=custom_programs,
        custom_programs_data=custom_programs_data
    )

@app.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    labels = []
    values = []
    selected_program_id = None

    if request.method == 'POST':
        custom_program_id = request.form.get('custom_program_id')
        selected_program_id = custom_program_id  # Set the selected program ID
        filter_period = request.form.get('period')
        start_date = None
        end_date = None

        # Date range handling
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

        if custom_program_id:
            program = ProgramDefinition.query.get_or_404(custom_program_id)
            numeric_fields = [field for field in program.fields if field.field_type == 'number']
            
            if numeric_fields:
                labels = [field.field_label for field in numeric_fields]
                data = ProgramData.query.filter(
                    ProgramData.program_id == custom_program_id
                ).all()

                # Filter data by date range
                filtered_data = []
                for entry in data:
                    entry_date = datetime.strptime(entry.data.get('date_column', ''), '%Y-%m-%d').date()
                    if start_date <= entry_date <= end_date:
                        filtered_data.append(entry)

                values = []
                for field in numeric_fields:
                    total = sum(
                        float(entry.data.get(field.field_name, 0) or 0)
                        for entry in filtered_data
                    )
                    values.append(total)

    # Get all custom programs for the dropdown
    custom_programs = ProgramDefinition.query.all()

    return render_template('reports.html', 
                         labels=labels, 
                         values=values, 
                         custom_programs=custom_programs,
                         selected_program_id=selected_program_id)

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
    
    # Format dates before passing to template
    for child in children:
        if child.date_of_birth and not isinstance(child.date_of_birth, str):
            child.date_of_birth = child.date_of_birth.strftime('%Y-%m-%d')
    
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
    custom_programs = ProgramDefinition.query.all()
    
    # Format dates for education and family indicators
    for indicator in education_indicators:
        try:
            if indicator.date_column and not isinstance(indicator.date_column, str):
                indicator.date_column = indicator.date_column.strftime('%Y-%m-%d')
        except Exception as e:
            indicator.date_column = None
            
    for indicator in family_indicators:
        try:
            if indicator.date_column and not isinstance(indicator.date_column, str):
                indicator.date_column = indicator.date_column.strftime('%Y-%m-%d')
        except Exception as e:
            indicator.date_column = None
    
    # Get data for each custom program
    for program in custom_programs:
        program.data = ProgramData.query.filter_by(program_id=program.id).order_by(ProgramData.created_at.desc()).all()
    
    return render_template('indicators_display.html', 
                         education_indicators=education_indicators,
                         family_indicators=family_indicators,
                         custom_programs=custom_programs)

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

@app.route('/programs')
@login_required
def list_programs():
    programs = ProgramDefinition.query.all()
    return render_template('programs/list.html', programs=programs)

@app.route('/programs/new', methods=['GET', 'POST'])
@login_required
@handle_errors
def create_program():
    if current_user.role != 'admin':
        flash('You do not have permission to create programs.', 'danger')
        return redirect(url_for('list_programs'))

    if request.method == 'POST':
        try:
            program = ProgramDefinition(
                name=request.form['name'],
                description=request.form['description'],
                created_by=current_user.id
            )
            db.session.add(program)
            db.session.flush()

            # Process fields
            field_names = request.form.getlist('field_name[]')
            field_labels = request.form.getlist('field_label[]')
            field_types = request.form.getlist('field_type[]')
            field_required = request.form.getlist('field_required[]')

            # Add date_column field first
            date_field = ProgramField(
                program_id=program.id,
                field_name='date_column',
                field_label='Date',
                field_type='date',
                is_required=True,
                order=0
            )
            db.session.add(date_field)

            # Process other fields
            for i in range(len(field_names)):
                field = ProgramField(
                    program_id=program.id,
                    field_name=field_names[i],
                    field_label=field_labels[i],
                    field_type=field_types[i],
                    is_required=field_required[i] == 'true',
                    order=i + 1
                )
                db.session.add(field)

            db.session.commit()
            flash('Program created successfully!', 'success')
            return redirect(url_for('list_programs'))
        except Exception as e:
            db.session.rollback()
            raise e

    return render_template('programs/create.html')

@app.route('/programs/<int:program_id>/data/new', methods=['GET', 'POST'])
@login_required
def add_program_data(program_id):
    program = ProgramDefinition.query.get_or_404(program_id)
    
    if request.method == 'POST':
        try:
            data = {}
            for field in program.fields:
                value = request.form.get(field.field_name)
                if field.is_required and not value:
                    raise ValueError(f"{field.field_label} is required")
                
                # Convert value based on field type
                if field.field_type == 'number':
                    value = float(value) if value else 0
                elif field.field_type == 'date':
                    if field.field_name == 'date_column':
                        # Use current date if not provided
                        date_value = datetime.strptime(value, '%Y-%m-%d').date() if value else datetime.now().date()
                        value = date_value.strftime('%Y-%m-%d')  # Convert to string
                    else:
                        date_value = datetime.strptime(value, '%Y-%m-%d').date() if value else None
                        value = date_value.strftime('%Y-%m-%d') if date_value else None
                
                data[field.field_name] = value

            program_data = ProgramData(
                program_id=program_id,
                data=data,
                created_by=current_user.id
            )
            db.session.add(program_data)
            db.session.commit()
            
            flash('Data added successfully!', 'success')
            return redirect(url_for('view_program_data', program_id=program_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding data: {str(e)}', 'danger')

    return render_template('programs/add_data.html', program=program)

@app.route('/programs/<int:program_id>/data')
@login_required
def view_program_data(program_id):
    program = ProgramDefinition.query.get_or_404(program_id)
    data = ProgramData.query.filter_by(program_id=program_id).order_by(ProgramData.created_at.desc()).all()
    return render_template('programs/view_data.html', program=program, data=data)

@app.route('/programs/dashboard', methods=['GET', 'POST'])
@login_required
def programs_dashboard():
    # Get filter parameters
    filter_period = request.form.get('filter-period', 'this-month')
    start_date = None
    end_date = None

    today = datetime.today()

    if filter_period == 'this-month':
        start_date = today.replace(day=1)
        end_date = today
    elif filter_period == 'last-3-months':
        start_date = today - timedelta(days=90)
        end_date = today
    elif filter_period == 'this-year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif filter_period == 'custom':
        start_date_str = request.form.get('start-date')
        end_date_str = request.form.get('end-date')
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Get all programs with numeric fields
    programs = ProgramDefinition.query.all()
    programs_data = {}
    
    for program in programs:
        numeric_fields = [field for field in program.fields if field.field_type == 'number']
        if numeric_fields:  # Only include programs with numeric fields
            # Base query for program data
            data_query = ProgramData.query.filter_by(program_id=program.id)
            
            # Get all data entries
            data_entries = data_query.order_by(ProgramData.created_at).all()
            
            # Filter data by date range if dates are provided
            if start_date and end_date:
                filtered_entries = []
                for entry in data_entries:
                    entry_date = None
                    # Try to get date from date_column in data JSON
                    if 'date_column' in entry.data:
                        try:
                            entry_date = datetime.strptime(entry.data['date_column'], '%Y-%m-%d')
                        except (ValueError, TypeError):
                            pass
                    # Fallback to created_at if date_column is not valid
                    if not entry_date:
                        entry_date = entry.created_at
                    
                    if start_date.date() <= entry_date.date() <= end_date.date():
                        filtered_entries.append(entry)
                data_entries = filtered_entries
            
            # Prepare data for charts
            chart_data = {}
            for field in numeric_fields:
                field_data = {
                    'label': field.field_label,
                    'data': []
                }
                
                for entry in data_entries:
                    if field.field_name in entry.data:
                        try:
                            value = float(entry.data[field.field_name])
                            field_data['data'].append({
                                'date': entry.data.get('date_column', entry.created_at.strftime('%Y-%m-%d')),
                                'value': value
                            })
                        except (ValueError, TypeError):
                            continue
                
                if field_data['data']:  # Only include fields with valid data
                    chart_data[field.field_name] = field_data
            
            if chart_data:  # Only include programs with valid chart data
                programs_data[program.id] = {
                    'name': program.name,
                    'chart_data': chart_data
                }

    # Pagination for programs
    page = int(request.args.get('page', 1))
    per_page = 2  # Show 2 programs per page
    program_ids = list(programs_data.keys())
    total_pages = ceil(len(program_ids) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_programs = {pid: programs_data[pid] for pid in program_ids[start:end]}

    return render_template('programs/dashboard.html',
                         programs_data=paginated_programs,
                         filter_period=filter_period,
                         start_date=start_date,
                         end_date=end_date,
                         page=page,
                         total_pages=total_pages)

@app.route('/programs/<int:program_id>/delete', methods=['POST'])
@login_required
def delete_program(program_id):
    if current_user.role != 'admin':
        flash('You do not have permission to delete programs.', 'danger')
        return redirect(url_for('list_programs'))

    try:
        program = ProgramDefinition.query.get_or_404(program_id)
        
        # Delete all associated data first
        ProgramData.query.filter_by(program_id=program_id).delete()
        
        # Delete all associated fields
        ProgramField.query.filter_by(program_id=program_id).delete()
        
        # Delete the program
        db.session.delete(program)
        db.session.commit()
        
        flash('Program deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting program: {str(e)}', 'danger')

    return redirect(url_for('list_programs'))

@app.route('/user_management')
@login_required
def user_management():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('user_management.html', users=users)

@app.route('/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    
    if not all([username, password, role]):
        flash('All fields are required', 'danger')
        return redirect(url_for('user_management'))
    
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('user_management'))
    
    try:
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'danger')
    
    return redirect(url_for('user_management'))

@app.route('/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    user = User.query.get_or_404(user_id)
    try:
        # Generate a random password
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user.password = generate_password_hash(new_password)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Password reset successfully. New password: {new_password}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the admin user
    if user.username == 'admin':
        return jsonify({'success': False, 'message': 'Cannot delete the admin user'})
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/programs', methods=['POST'])
def create_program_api():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'name' not in data:
            return jsonify({'error': 'Program name is required'}), 400
            
        # Create new program
        program = ProgramDefinition(
            name=data['name'],
            description=data.get('description', '')
        )
        db.session.add(program)
        
        # Add program fields if provided
        if 'fields' in data and isinstance(data['fields'], list):
            for field_data in data['fields']:
                field = ProgramField(
                    program=program,
                    field_name=field_data['field_name'],
                    field_label=field_data['field_label'],
                    field_type=field_data['field_type'],
                    is_required=field_data.get('is_required', True),
                    validation_rules=json.dumps(field_data.get('validation_rules', {}))
                )
                db.session.add(field)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Program created successfully',
            'program_id': program.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/programs/<int:program_id>', methods=['GET'])
def get_program_api(program_id):
    program = ProgramDefinition.query.get_or_404(program_id)
    return jsonify({
        'id': program.id,
        'name': program.name,
        'description': program.description,
        'created_at': program.created_at.isoformat(),
        'fields': [{
            'field_name': field.field_name,
            'field_label': field.field_label,
            'field_type': field.field_type,
            'is_required': field.is_required,
            'validation_rules': json.loads(field.validation_rules) if field.validation_rules else {}
        } for field in program.fields]
    })

@app.route('/api/programs', methods=['GET'])
def list_programs_api():
    programs = ProgramDefinition.query.all()
    return jsonify([{
        'id': program.id,
        'name': program.name,
        'description': program.description,
        'created_at': program.created_at.isoformat(),
        'field_count': len(program.fields)
    } for program in programs])

if __name__ == '__main__':
    with app.app_context():
        # Create all database tables
        db.create_all()
        # Run the application
        app.run(debug=True)
