from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def seed_database():
    """Siembra datos iniciales si la base de datos no tiene usuarios."""
    from app.models import Usuario, Producto, Movimiento

    if Usuario.query.first() is None:
        # 1. Usuarios iniciales
        admin = Usuario(username='admin', rol='admin')
        admin.set_password('admin123')

        empleado = Usuario(username='empleado', rol='empleado')
        empleado.set_password('empleado123')

        db.session.add(admin)
        db.session.add(empleado)

        # 2. Catálogo inicial de productos D1
        productos_iniciales = [
            Producto(nombre='Leche Entera Latti 1L', categoria='Lácteos', precio=3200, cantidad_stock=45, stock_minimo=15),
            Producto(nombre='Queso Mozzarella Latti 400g', categoria='Lácteos', precio=9800, cantidad_stock=18, stock_minimo=8),
            Producto(nombre='Yogurt Fresa Latti 1000g', categoria='Lácteos', precio=5400, cantidad_stock=4, stock_minimo=10),
            Producto(nombre='Arroz Blanco Kythos 1000g', categoria='Abarrotes', precio=3900, cantidad_stock=80, stock_minimo=25),
            Producto(nombre='Aceite Vegetal D1 900ml', categoria='Abarrotes', precio=7500, cantidad_stock=30, stock_minimo=10),
            Producto(nombre='Atún en Aceite Campomar 140g', categoria='Abarrotes', precio=4200, cantidad_stock=3, stock_minimo=12),
            Producto(nombre='Detergente Líquido Rendy 2000ml', categoria='Aseo', precio=12900, cantidad_stock=22, stock_minimo=6),
            Producto(nombre='Papel Higiénico Soft 4 rollos', categoria='Aseo', precio=6800, cantidad_stock=2, stock_minimo=8),
            Producto(nombre='Lavatrastes Crema Rendy 500g', categoria='Aseo', precio=3100, cantidad_stock=14, stock_minimo=5),
            Producto(nombre='Papas Fritas Onduladas D1 115g', categoria='Snacks', precio=2800, cantidad_stock=40, stock_minimo=15),
            Producto(nombre='Galletas de Mantequilla 200g', categoria='Snacks', precio=2200, cantidad_stock=35, stock_minimo=10),
            Producto(nombre='Agua Sin Gas D1 600ml', categoria='Bebidas', precio=1100, cantidad_stock=60, stock_minimo=20),
            Producto(nombre='Gaseosa Cola D1 1.5L', categoria='Bebidas', precio=2900, cantidad_stock=1, stock_minimo=10),
            Producto(nombre='Pan Tajado Blanco Horneado 450g', categoria='Panadería', precio=4100, cantidad_stock=12, stock_minimo=6),
        ]

        db.session.add_all(productos_iniciales)
        db.session.commit()

        # 3. Movimientos de entrada de apertura
        for prod in productos_iniciales:
            mov = Movimiento(
                producto_id=prod.id,
                tipo='entrada',
                cantidad=prod.cantidad_stock
            )
            db.session.add(mov)

        db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Import models
    from app import models

    # Register blueprint
    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        seed_database()

    return app
