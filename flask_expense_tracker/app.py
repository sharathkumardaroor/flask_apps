import os
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

BUDGET_LIMIT = 1000  # Example monthly budget

# Setup
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    expenses = db.relationship('Expense', backref='user', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        description = request.form['description']
        date = request.form['date'] or datetime.utcnow().date()
        expense = Expense(amount=amount, category=category, description=description, date=date, user_id=current_user.id)
        db.session.add(expense)
        db.session.commit()
        flash('Expense added!')
        return redirect(url_for('index'))
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses if e.date.month == datetime.utcnow().month and e.date.year == datetime.utcnow().year)
    over_budget = total > BUDGET_LIMIT
    return render_template('index.html', expenses=expenses, total=total, over_budget=over_budget, budget=BUDGET_LIMIT)

@app.route('/chart.png')
@login_required
def chart():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{'category': e.category, 'amount': e.amount} for e in expenses])
    fig, ax = plt.subplots()
    if not df.empty:
        df.groupby('category').sum().plot(kind='pie', y='amount', ax=ax, autopct='%1.1f%%')
    else:
        ax.text(0.5, 0.5, 'No data', ha='center')
    buf = BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/export')
@login_required
def export():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{'amount': e.amount, 'category': e.category, 'description': e.description, 'date': e.date} for e in expenses])
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(buf, mimetype='text/csv', as_attachment=True, download_name='expenses.csv')

if __name__ == '__main__':
    if not os.path.exists('flask_expense_tracker/expenses.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True) 