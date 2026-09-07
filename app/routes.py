from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from app.models import Producto, Movimiento
from app import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    total_productos = Producto.query.count()
    stock_bajo = Producto.query.filter(Producto.cantidad_stock <= Producto.stock_minimo).count()
    movimientos_hoy = Movimiento.query.filter(db.func.date(Movimiento.fecha) == date.today()).count()
    movimientos_recientes = Movimiento.query.order_by(Movimiento.fecha.desc()).limit(5).all()
    return render_template('index.html',
                           total_productos=total_productos,
                           stock_bajo=stock_bajo,
                           movimientos_hoy=movimientos_hoy,
                           movimientos_recientes=movimientos_recientes)

@main.route('/productos')
def listar_productos():
    productos = Producto.query.order_by(Producto.nombre).all()
    return render_template('productos.html', productos=productos)

@main.route('/productos/agregar', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        producto = Producto(
            nombre=request.form['nombre'],
            categoria=request.form['categoria'],
            precio=float(request.form['precio']),
            cantidad_stock=int(request.form['cantidad_stock']),
            stock_minimo=int(request.form['stock_minimo'])
        )
        db.session.add(producto)
        db.session.commit()
        flash('Producto agregado exitosamente.')
        return redirect(url_for('main.listar_productos'))
    return render_template('producto_form.html')

@main.route('/productos/<int:id>')
def detalle_producto(id):
    producto = Producto.query.get_or_404(id)
    movimientos = Movimiento.query.filter_by(producto_id=id).order_by(Movimiento.fecha.desc()).all()
    return render_template('producto_detalle.html', producto=producto, movimientos=movimientos)

@main.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.categoria = request.form['categoria']
        producto.precio = float(request.form['precio'])
        producto.cantidad_stock = int(request.form['cantidad_stock'])
        producto.stock_minimo = int(request.form['stock_minimo'])
        db.session.commit()
        flash('Producto actualizado exitosamente.')
        return redirect(url_for('main.detalle_producto', id=id))
    return render_template('producto_form.html', producto=producto)

@main.route('/productos/<int:id>/eliminar', methods=['POST'])
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado exitosamente.')
    return redirect(url_for('main.listar_productos'))

@main.route('/movimientos')
def listar_movimientos():
    movimientos = Movimiento.query.order_by(Movimiento.fecha.desc()).all()
    return render_template('movimientos.html', movimientos=movimientos)

@main.route('/movimientos/registrar', methods=['GET', 'POST'])
def registrar_movimiento():
    productos = Producto.query.order_by(Producto.nombre).all()
    producto_seleccionado = request.args.get('producto_id', None)
    if request.method == 'POST':
        producto = Producto.query.get_or_404(int(request.form['producto_id']))
        tipo = request.form['tipo']
        cantidad = int(request.form['cantidad'])
        if tipo == 'entrada':
            producto.cantidad_stock += cantidad
        else:
            if cantidad > producto.cantidad_stock:
                flash('Stock insuficiente para esta salida.')
                return redirect(url_for('main.registrar_movimiento'))
            producto.cantidad_stock -= cantidad
        movimiento = Movimiento(
            producto_id=producto.id,
            tipo=tipo,
            cantidad=cantidad
        )
        db.session.add(movimiento)
        db.session.commit()
        flash('Movimiento registrado exitosamente.')
        return redirect(url_for('main.listar_movimientos'))
    return render_template('movimiento_form.html', productos=productos, producto_seleccionado=producto_seleccionado)
