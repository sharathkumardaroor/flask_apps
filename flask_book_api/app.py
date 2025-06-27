import os
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    books = db.relationship('Book', backref='owner', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(username=username, password=hashed_pw)
        db.session.add(user)
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

@app.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    if search:
        books = Book.query.filter((Book.title.ilike(f'%{search}%')) | (Book.author.ilike(f'%{search}%'))).all()
    else:
        books = Book.query.all()
    return render_template('index.html', books=books, search=search)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form.get('year', type=int)
        description = request.form['description']
        book = Book(title=title, author=author, year=year, description=description, owner=current_user)
        db.session.add(book)
        db.session.commit()
        flash('Book added!')
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if not current_user.is_admin and book.owner != current_user:
        abort(403)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.year = request.form.get('year', type=int)
        book.description = request.form['description']
        db.session.commit()
        flash('Book updated!')
        return redirect(url_for('index'))
    return render_template('edit_book.html', book=book)

@app.route('/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if not current_user.is_admin and book.owner != current_user:
        abort(403)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted!')
    return redirect(url_for('index'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return render_template('admin_users.html', users=users)

if __name__ == '__main__':
    if not os.path.exists('flask_book_api/books.db'):
        with app.app_context():
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', password=generate_password_hash('admin', method='pbkdf2:sha256'), is_admin=True)
                db.session.add(admin)
                db.session.commit()
    app.run(debug=True) 