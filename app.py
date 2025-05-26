from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carbon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos de la base de datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Calculation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    km = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('calculations', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registro exitoso. Por favor inicia sesión.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Ruta principal
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    history = []
    
    if current_user.is_authenticated:
        if request.method == "POST":
            try:
                km = float(request.form["km"])
                huella = km * 0.192
                result = f"Tu huella semanal estimada es de {huella:.2f} kg de CO₂"
                
                # Guardar en la base de datos
                calculation = Calculation(
                    km=km,
                    co2=huella,
                    user_id=current_user.id
                )
                db.session.add(calculation)
                db.session.commit()
                
            except ValueError:
                result = "Por favor, ingresa un número válido."
        
        # Obtener historial del usuario
        history = Calculation.query.filter_by(user_id=current_user.id).order_by(Calculation.date.desc()).all()
    
    return render_template("index.html", result=result, history=history)

@app.route('/init_db')
def init_db():
    db.create_all()
    return 'Base de datos inicializada'

if __name__ == "__main__":
    app.run()