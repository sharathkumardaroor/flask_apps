import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(300))
    reviews = db.relationship('Review', backref='product', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Auth routes
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
    session.pop('cart', None)
    return redirect(url_for('login'))

# Product listing
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

# Product detail and reviews
@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form['content']
        rating = int(request.form['rating'])
        review = Review(content=content, rating=rating, user_id=current_user.id, product_id=product.id)
        db.session.add(review)
        db.session.commit()
        flash('Review added!')
        return redirect(url_for('product_detail', product_id=product_id))
    return render_template('product_detail.html', product=product)

# Cart
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    session['cart'] = cart
    flash('Added to cart!')
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            items.append({'product': product, 'quantity': qty, 'subtotal': product.price * qty})
            total += product.price * qty
    return render_template('cart.html', items=items, total=total)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    return redirect(url_for('cart'))

# Checkout
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty!')
        return redirect(url_for('index'))
    if request.method == 'POST':
        order = Order(user_id=current_user.id)
        db.session.add(order)
        db.session.commit()
        for pid, qty in cart.items():
            product = Product.query.get(int(pid))
            if product:
                item = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, price=product.price)
                db.session.add(item)
        db.session.commit()
        session.pop('cart', None)
        flash('Order placed successfully!')
        return redirect(url_for('orders'))
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            items.append({'product': product, 'quantity': qty, 'subtotal': product.price * qty})
            total += product.price * qty
    return render_template('checkout.html', items=items, total=total)

# Order history
@app.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

if __name__ == '__main__':
    if not os.path.exists('flask_ecommerce_store/ecommerce.db'):
        with app.app_context():
            db.create_all()
            # Add some sample products
            if not Product.query.first():
                sample_products = [
                    Product(name='Laptop', description='A powerful laptop.', price=60000, image='https://via.placeholder.com/150'),
                    Product(name='Smartphone', description='A modern smartphone.', price=20000, image='https://via.placeholder.com/150'),
                    Product(name='Headphones', description='Noise-cancelling headphones.', price=5000, image='https://via.placeholder.com/150'),
                ]
                db.session.add_all(sample_products)
                db.session.commit()
    app.run(debug=True) 