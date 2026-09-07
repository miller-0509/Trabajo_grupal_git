from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Usuario(db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), default='empleado', nullable=False)

    def set_password(self, password_text):
        """Genera el hash de la contraseña y lo almacena."""
        self.password = generate_password_hash(password_text)

    def check_password(self, password_text):
        """Verifica si la contraseña coincide con el hash almacenado."""
        return check_password_hash(self.password, password_text)

    def __repr__(self):
        return f'<Usuario {self.username} (Rol: {self.rol})>'


class Producto(db.Model):
    __tablename__ = 'producto'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(100), nullable=True)
    precio = db.Column(db.Float, nullable=False)
    cantidad_stock = db.Column(db.Integer, default=0, nullable=False)
    stock_minimo = db.Column(db.Integer, default=5, nullable=False)
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con Movimiento
    movimientos = db.relationship('Movimiento', backref='producto', lazy=True, cascade='all, delete-orphan')

    def esta_bajo_stock(self):
        """Determina si el producto está en o por debajo de su stock mínimo."""
        return self.cantidad_stock <= self.stock_minimo

    def __repr__(self):
        return f'<Producto {self.nombre} (Stock: {self.cantidad_stock}, Precio: ${self.precio})>'


class Movimiento(db.Model):
    __tablename__ = 'movimiento'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'entrada' o 'salida'
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Movimiento {self.tipo} - {self.cantidad} unidades (Producto ID: {self.producto_id})>'
