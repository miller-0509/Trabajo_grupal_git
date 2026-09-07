from functools import wraps
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from app import db
from app.models import Usuario, Producto, Movimiento

main = Blueprint('main', __name__)


# ============================================================================
# DECORADORES DE AUTENTICACIÓN Y AUTORIZACIÓN
# ============================================================================

def login_required(f):
    """Decorador que requiere que el usuario esté autenticado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('main.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador que requiere que el usuario sea administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('main.login', next=request.path))
        if session.get('usuario_rol') != 'admin':
            flash('No tienes permisos de administrador para acceder a esta sección.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# CONTEXTO GLOBAL
# ============================================================================

@main.before_app_request
def cargar_usuario_actual():
    """Carga los datos del usuario actual en g para uso en templates."""
    g.usuario = None
    if 'usuario_id' in session:
        g.usuario = db.session.get(Usuario, session['usuario_id'])
        if g.usuario is None:
            # El usuario ya no existe en la BD, limpiar sesión
            session.clear()


@main.app_context_processor
def inject_global_vars():
    """Inyecta variables globales en todos los templates."""
    return dict(
        usuario_actual=getattr(g, 'usuario', None),
        now=datetime.utcnow()
    )


# ============================================================================
# RUTAS DE AUTENTICACIÓN Y PERFIL
# ============================================================================

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión de usuario."""
    if 'usuario_id' in session:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('login.html')

        usuario = Usuario.query.filter_by(username=username).first()

        if usuario is None or not usuario.check_password(password):
            flash('Usuario o contraseña incorrectos.', 'error')
            return render_template('login.html')

        # Iniciar sesión
        session.clear()
        session['usuario_id'] = usuario.id
        session['usuario_username'] = usuario.username
        session['usuario_rol'] = usuario.rol

        flash(f'¡Bienvenido, {usuario.username}!', 'success')
        next_page = request.args.get('next') or url_for('main.index')
        return redirect(next_page)

    return render_template('login.html')


@main.route('/logout')
def logout():
    """Cerrar sesión del usuario."""
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('main.login'))


@main.route('/registro', methods=['GET', 'POST'])
def registro():
    """Registro de nuevo usuario.
    - Si no hay usuarios en el sistema, permite crear el primer admin sin login.
    - En cualquier otro caso, solo un admin autenticado puede registrar usuarios.
    """
    total_usuarios = Usuario.query.count()
    es_primer_usuario = total_usuarios == 0

    if not es_primer_usuario:
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para registrar usuarios.', 'warning')
            return redirect(url_for('main.login'))
        if session.get('usuario_rol') != 'admin':
            flash('Solo los administradores pueden registrar nuevos usuarios.', 'error')
            return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirmar_password = request.form.get('confirmar_password', '').strip()
        rol = request.form.get('rol', 'empleado')

        errores = []

        if not username:
            errores.append('El nombre de usuario es obligatorio.')
        elif len(username) < 3:
            errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
        elif len(username) > 80:
            errores.append('El nombre de usuario no puede exceder 80 caracteres.')

        if not password:
            errores.append('La contraseña es obligatoria.')
        elif len(password) < 6:
            errores.append('La contraseña debe tener al menos 6 caracteres.')

        if password != confirmar_password:
            errores.append('Las contraseñas no coinciden.')

        if rol not in ('admin', 'empleado'):
            errores.append('Rol no válido. Debe ser "admin" o "empleado".')

        if username and Usuario.query.filter_by(username=username).first():
            errores.append('El nombre de usuario ya está en uso.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('registro.html', es_primer_usuario=es_primer_usuario)

        try:
            nuevo_usuario = Usuario(
                username=username,
                rol='admin' if es_primer_usuario else rol
            )
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
            db.session.commit()

            if es_primer_usuario:
                flash('¡Cuenta de administrador creada exitosamente! Inicia sesión para continuar.', 'success')
                return redirect(url_for('main.login'))
            else:
                flash(f'Usuario "{username}" registrado exitosamente.', 'success')
                return redirect(url_for('main.listar_usuarios'))
        except Exception:
            db.session.rollback()
            flash('Error al crear el usuario. Inténtalo de nuevo.', 'error')
            return render_template('registro.html', es_primer_usuario=es_primer_usuario)

    return render_template('registro.html', es_primer_usuario=es_primer_usuario)


@main.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Ver y editar el perfil del usuario actual (cambiar contraseña)."""
    usuario = db.session.get(Usuario, session['usuario_id'])
    if not usuario:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('main.logout'))

    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '').strip()
        nueva_password = request.form.get('password', '').strip()
        confirmar_password = request.form.get('confirmar_password', '').strip()

        if not password_actual:
            flash('Debes ingresar tu contraseña actual.', 'error')
            return render_template('perfil.html', usuario=usuario)

        if not usuario.check_password(password_actual):
            flash('La contraseña actual es incorrecta.', 'error')
            return render_template('perfil.html', usuario=usuario)

        if not nueva_password:
            flash('Debes ingresar una nueva contraseña.', 'error')
            return render_template('perfil.html', usuario=usuario)

        if len(nueva_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('perfil.html', usuario=usuario)

        if nueva_password != confirmar_password:
            flash('Las contraseñas nuevas no coinciden.', 'error')
            return render_template('perfil.html', usuario=usuario)

        try:
            usuario.set_password(nueva_password)
            db.session.commit()
            flash('Contraseña actualizada exitosamente.', 'success')
        except Exception:
            db.session.rollback()
            flash('Error al actualizar la contraseña.', 'error')

        return render_template('perfil.html', usuario=usuario)

    return render_template('perfil.html', usuario=usuario)


# ============================================================================
# GESTIÓN DE USUARIOS (Solo Administradores)
# ============================================================================

@main.route('/usuarios')
@admin_required
def listar_usuarios():
    """Lista todos los usuarios registrados."""
    usuarios = Usuario.query.order_by(Usuario.username).all()
    return render_template('usuarios.html', usuarios=usuarios)


@main.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    """Editar un usuario existente."""
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('main.listar_usuarios'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        rol = request.form.get('rol', 'empleado')
        nueva_password = request.form.get('password', '').strip()

        errores = []

        if not username:
            errores.append('El nombre de usuario es obligatorio.')
        elif len(username) < 3:
            errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
        elif len(username) > 80:
            errores.append('El nombre de usuario no puede exceder 80 caracteres.')

        if rol not in ('admin', 'empleado'):
            errores.append('Rol no válido. Debe ser "admin" o "empleado".')

        if username != usuario.username:
            existente = Usuario.query.filter_by(username=username).first()
            if existente:
                errores.append('El nombre de usuario ya está en uso por otro usuario.')

        if usuario.rol == 'admin' and rol != 'admin':
            admin_count = Usuario.query.filter_by(rol='admin').count()
            if admin_count <= 1:
                errores.append('No puedes quitarle el rol de admin al único administrador del sistema.')

        if nueva_password and len(nueva_password) < 6:
            errores.append('La nueva contraseña debe tener al menos 6 caracteres.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('usuario_form.html', usuario=usuario)

        try:
            usuario.username = username
            usuario.rol = rol
            if nueva_password:
                usuario.set_password(nueva_password)
            db.session.commit()

            # Si el admin editó su propio usuario, actualizar sesión
            if usuario.id == session.get('usuario_id'):
                session['usuario_username'] = usuario.username
                session['usuario_rol'] = usuario.rol

            flash(f'Usuario "{username}" actualizado exitosamente.', 'success')
            return redirect(url_for('main.listar_usuarios'))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar el usuario.', 'error')
            return render_template('usuario_form.html', usuario=usuario)

    return render_template('usuario_form.html', usuario=usuario)


@main.route('/usuarios/<int:id>/eliminar', methods=['POST'])
@admin_required
def eliminar_usuario(id):
    """Eliminar un usuario."""
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('main.listar_usuarios'))

    if usuario.id == session.get('usuario_id'):
        flash('No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('main.listar_usuarios'))

    if usuario.rol == 'admin':
        admin_count = Usuario.query.filter_by(rol='admin').count()
        if admin_count <= 1:
            flash('No puedes eliminar al único administrador del sistema.', 'error')
            return redirect(url_for('main.listar_usuarios'))

    try:
        nombre = usuario.username
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario "{nombre}" eliminado exitosamente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar el usuario.', 'error')

    return redirect(url_for('main.listar_usuarios'))


# ============================================================================
# DASHBOARD PRINCIPAL
# ============================================================================

@main.route('/')
@main.route('/dashboard')
@login_required
def index():
    """Dashboard principal con estadísticas e indicadores clave."""
    total_productos = Producto.query.count()
    stock_bajo = Producto.query.filter(
        Producto.cantidad_stock <= Producto.stock_minimo
    ).count()
    movimientos_hoy = Movimiento.query.filter(
        db.func.date(Movimiento.fecha) == date.today()
    ).count()
    movimientos_recientes = Movimiento.query.order_by(
        Movimiento.fecha.desc()
    ).limit(5).all()

    total_usuarios = Usuario.query.count()
    total_movimientos = Movimiento.query.count()
    valor_inventario = db.session.query(
        db.func.sum(Producto.precio * Producto.cantidad_stock)
    ).scalar() or 0.0

    return render_template('index.html',
                           total_productos=total_productos,
                           stock_bajo=stock_bajo,
                           movimientos_hoy=movimientos_hoy,
                           movimientos_recientes=movimientos_recientes,
                           total_usuarios=total_usuarios,
                           total_movimientos=total_movimientos,
                           valor_inventario=valor_inventario)


# ============================================================================
# GESTIÓN DE PRODUCTOS (CRUD)
# ============================================================================

@main.route('/productos')
@login_required
def listar_productos():
    """Lista todos los productos del inventario ordenados por nombre."""
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    return render_template('productos.html', productos=productos)


@main.route('/productos/buscar')
@login_required
def buscar_productos():
    """Buscar productos por nombre o categoría."""
    query = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', '').strip()

    productos_query = Producto.query

    if query:
        productos_query = productos_query.filter(
            db.or_(
                Producto.nombre.ilike(f'%{query}%'),
                Producto.categoria.ilike(f'%{query}%')
            )
        )

    if categoria:
        productos_query = productos_query.filter(
            Producto.categoria.ilike(f'%{categoria}%')
        )

    productos = productos_query.order_by(Producto.nombre.asc()).all()

    categorias = db.session.query(
        Producto.categoria
    ).distinct().order_by(Producto.categoria).all()
    categorias = [c[0] for c in categorias if c[0]]

    return render_template('buscar_productos.html',
                           productos=productos,
                           query=query,
                           categoria_seleccionada=categoria,
                           categorias=categorias)


@main.route('/productos/stock-bajo')
@login_required
def stock_bajo():
    """Lista productos con stock bajo (menor o igual al mínimo)."""
    productos = Producto.query.filter(
        Producto.cantidad_stock <= Producto.stock_minimo
    ).order_by(Producto.cantidad_stock.asc()).all()
    return render_template('stock_bajo.html', productos=productos)


@main.route('/productos/agregar', methods=['GET', 'POST'])
@main.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    """Agregar un nuevo producto al inventario."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        categoria = request.form.get('categoria', '').strip()
        precio_str = request.form.get('precio', '').strip()
        cantidad_stock_str = request.form.get('cantidad_stock', '0').strip()
        stock_minimo_str = request.form.get('stock_minimo', '5').strip()

        errores = []
        precio = None
        cantidad_stock = None
        stock_minimo = None

        if not nombre:
            errores.append('El nombre del producto es obligatorio.')
        elif len(nombre) > 150:
            errores.append('El nombre no puede exceder 150 caracteres.')

        if not precio_str:
            errores.append('El precio es obligatorio.')
        else:
            try:
                precio = float(precio_str)
                if precio < 0:
                    errores.append('El precio no puede ser negativo.')
            except ValueError:
                errores.append('El precio debe ser un número válido.')

        try:
            cantidad_stock = int(cantidad_stock_str) if cantidad_stock_str else 0
            if cantidad_stock < 0:
                errores.append('La cantidad en stock no puede ser negativa.')
        except ValueError:
            errores.append('La cantidad en stock debe ser un número entero.')

        try:
            stock_minimo = int(stock_minimo_str) if stock_minimo_str else 5
            if stock_minimo < 0:
                errores.append('El stock mínimo no puede ser negativo.')
        except ValueError:
            errores.append('El stock mínimo debe ser un número entero.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('producto_form.html', producto=None)

        try:
            producto = Producto(
                nombre=nombre,
                categoria=categoria if categoria else 'General',
                precio=precio,
                cantidad_stock=cantidad_stock,
                stock_minimo=stock_minimo
            )
            db.session.add(producto)
            db.session.commit()

            # Si inicia con stock, registrar movimiento de entrada
            if cantidad_stock > 0:
                mov = Movimiento(
                    producto_id=producto.id,
                    tipo='entrada',
                    cantidad=cantidad_stock
                )
                db.session.add(mov)
                db.session.commit()

            flash(f'Producto "{nombre}" agregado exitosamente.', 'success')
            return redirect(url_for('main.listar_productos'))
        except Exception:
            db.session.rollback()
            flash('Error al agregar el producto. Inténtalo de nuevo.', 'error')
            return render_template('producto_form.html', producto=None)

    return render_template('producto_form.html', producto=None)


@main.route('/productos/<int:id>')
@login_required
def detalle_producto(id):
    """Ver detalle de un producto y su historial de movimientos."""
    producto = db.session.get(Producto, id)
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('main.listar_productos'))

    movimientos = Movimiento.query.filter_by(
        producto_id=id
    ).order_by(Movimiento.fecha.desc()).all()

    return render_template('producto_detalle.html',
                           producto=producto,
                           movimientos=movimientos)


@main.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    """Editar un producto existente."""
    producto = db.session.get(Producto, id)
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('main.listar_productos'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        categoria = request.form.get('categoria', '').strip()
        precio_str = request.form.get('precio', '').strip()
        cantidad_stock_str = request.form.get('cantidad_stock', '').strip()
        stock_minimo_str = request.form.get('stock_minimo', '').strip()

        errores = []
        precio = None
        cantidad_stock = None
        stock_minimo = None

        if not nombre:
            errores.append('El nombre del producto es obligatorio.')
        elif len(nombre) > 150:
            errores.append('El nombre no puede exceder 150 caracteres.')

        if not precio_str:
            errores.append('El precio es obligatorio.')
        else:
            try:
                precio = float(precio_str)
                if precio < 0:
                    errores.append('El precio no puede ser negativo.')
            except ValueError:
                errores.append('El precio debe ser un número válido.')

        if not cantidad_stock_str:
            errores.append('La cantidad en stock es obligatoria.')
        else:
            try:
                cantidad_stock = int(cantidad_stock_str)
                if cantidad_stock < 0:
                    errores.append('La cantidad en stock no puede ser negativa.')
            except ValueError:
                errores.append('La cantidad en stock debe ser un número entero.')

        if not stock_minimo_str:
            errores.append('El stock mínimo es obligatorio.')
        else:
            try:
                stock_minimo = int(stock_minimo_str)
                if stock_minimo < 0:
                    errores.append('El stock mínimo no puede ser negativo.')
            except ValueError:
                errores.append('El stock mínimo debe ser un número entero.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('producto_form.html', producto=producto)

        try:
            producto.nombre = nombre
            producto.categoria = categoria if categoria else 'General'
            producto.precio = precio
            producto.cantidad_stock = cantidad_stock
            producto.stock_minimo = stock_minimo
            db.session.commit()
            flash(f'Producto "{nombre}" actualizado exitosamente.', 'success')
            return redirect(url_for('main.detalle_producto', id=id))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar el producto.', 'error')
            return render_template('producto_form.html', producto=producto)

    return render_template('producto_form.html', producto=producto)


@main.route('/productos/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(id):
    """Eliminar un producto y todos sus movimientos asociados (cascade)."""
    producto = db.session.get(Producto, id)
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('main.listar_productos'))

    try:
        nombre = producto.nombre
        db.session.delete(producto)
        db.session.commit()
        flash(f'Producto "{nombre}" eliminado exitosamente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar el producto.', 'error')

    return redirect(url_for('main.listar_productos'))


# ============================================================================
# MOVIMIENTOS DE INVENTARIO (Entradas y Salidas)
# ============================================================================

@main.route('/movimientos')
@login_required
def listar_movimientos():
    """Lista todos los movimientos ordenados por fecha descendente."""
    movimientos = Movimiento.query.order_by(Movimiento.fecha.desc()).all()
    return render_template('movimientos.html', movimientos=movimientos)


@main.route('/movimientos/nuevo', methods=['GET', 'POST'])
@main.route('/movimientos/registrar', methods=['GET', 'POST'])
@login_required
def registrar_movimiento():
    """Registrar un nuevo movimiento (entrada o salida) y actualizar stock."""
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    producto_preseleccionado = request.args.get('producto_id', type=int)

    if request.method == 'POST':
        producto_id = request.form.get('producto_id', type=int)
        tipo = request.form.get('tipo', '').strip()
        cantidad = request.form.get('cantidad', type=int)

        if not producto_id or not tipo or not cantidad:
            flash('Todos los campos son obligatorios.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_preseleccionado)

        if cantidad <= 0:
            flash('La cantidad debe ser mayor a cero.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_id)

        if tipo not in ('entrada', 'salida'):
            flash('Tipo de movimiento no válido.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_id)

        producto = db.session.get(Producto, producto_id)
        if not producto:
            flash('Producto no encontrado.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_preseleccionado)

        # Validación de stock suficiente para salidas
        if tipo == 'salida' and producto.cantidad_stock < cantidad:
            flash(
                f'Stock insuficiente para "{producto.nombre}". '
                f'Disponible: {producto.cantidad_stock}, solicitado: {cantidad}.',
                'error'
            )
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto.id)

        try:
            # Actualizar stock
            if tipo == 'entrada':
                producto.cantidad_stock += cantidad
            else:
                producto.cantidad_stock -= cantidad

            # Crear registro de movimiento
            movimiento = Movimiento(
                producto_id=producto.id,
                tipo=tipo,
                cantidad=cantidad
            )
            db.session.add(movimiento)
            db.session.commit()

            flash(
                f'Movimiento de {tipo} registrado exitosamente. '
                f'Nuevo stock de "{producto.nombre}": {producto.cantidad_stock}.',
                'success'
            )
            return redirect(url_for('main.listar_movimientos'))
        except Exception:
            db.session.rollback()
            flash('Error al registrar el movimiento.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto.id)

    return render_template('movimiento_form.html',
                           productos=productos,
                           producto_seleccionado=producto_preseleccionado)


@main.route('/movimientos/<int:id>')
@login_required
def detalle_movimiento(id):
    """Ver detalle de un movimiento específico."""
    movimiento = db.session.get(Movimiento, id)
    if not movimiento:
        flash('Movimiento no encontrado.', 'error')
        return redirect(url_for('main.listar_movimientos'))
    return render_template('movimiento_detalle.html', movimiento=movimiento)


@main.route('/movimientos/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_movimiento(id):
    """Eliminar un movimiento y revertir su efecto en el stock del producto."""
    movimiento = db.session.get(Movimiento, id)
    if not movimiento:
        flash('Movimiento no encontrado.', 'error')
        return redirect(url_for('main.listar_movimientos'))

    producto = db.session.get(Producto, movimiento.producto_id)

    try:
        # Revertir el efecto en el stock si el producto todavía existe
        if producto:
            if movimiento.tipo == 'entrada':
                if producto.cantidad_stock < movimiento.cantidad:
                    flash(
                        f'No se puede eliminar la entrada: el stock actual ({producto.cantidad_stock}) '
                        f'es menor a la cantidad a revertir ({movimiento.cantidad}).',
                        'error'
                    )
                    return redirect(url_for('main.detalle_movimiento', id=id))
                producto.cantidad_stock -= movimiento.cantidad
            elif movimiento.tipo == 'salida':
                producto.cantidad_stock += movimiento.cantidad

        db.session.delete(movimiento)
        db.session.commit()
        flash('Movimiento eliminado y stock revertido exitosamente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar el movimiento.', 'error')

    return redirect(url_for('main.listar_movimientos'))


# ============================================================================
# REPORTES Y ESTADÍSTICAS
# ============================================================================

@main.route('/reportes')
@login_required
def reportes():
    """Genera reportes y estadísticas del inventario."""
    total_productos = Producto.query.count()
    total_movimientos = Movimiento.query.count()

    movimientos_hoy = Movimiento.query.filter(
        db.func.date(Movimiento.fecha) == date.today()
    ).count()

    valor_inventario = db.session.query(
        db.func.sum(Producto.precio * Producto.cantidad_stock)
    ).scalar() or 0.0

    total_entradas = Movimiento.query.filter_by(tipo='entrada').count()
    total_salidas = Movimiento.query.filter_by(tipo='salida').count()

    productos_stock_bajo = Producto.query.filter(
        Producto.cantidad_stock <= Producto.stock_minimo
    ).order_by(Producto.cantidad_stock.asc()).all()

    # Top 5 productos con más movimientos
    top_movidos_query = db.session.query(
        Producto.nombre,
        db.func.count(Movimiento.id).label('total_movs')
    ).join(Movimiento, Producto.id == Movimiento.producto_id)\
     .group_by(Producto.id, Producto.nombre)\
     .order_by(db.desc('total_movs'))\
     .limit(5).all()

    # Distribución por categorías
    categorias_query = db.session.query(
        Producto.categoria,
        db.func.count(Producto.id).label('total_prods')
    ).group_by(Producto.categoria)\
     .order_by(db.desc('total_prods')).all()

    return render_template('reportes.html',
                           total_productos=total_productos,
                           total_movimientos=total_movimientos,
                           movimientos_hoy=movimientos_hoy,
                           valor_inventario=valor_inventario,
                           total_entradas=total_entradas,
                           total_salidas=total_salidas,
                           productos_stock_bajo=productos_stock_bajo,
                           productos_mas_movidos=top_movidos_query,
                           categorias=categorias_query)


# ============================================================================
# MANEJADORES DE ERRORES HTTP
# ============================================================================

@main.app_errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404


@main.app_errorhandler(500)
def error_500(error):
    db.session.rollback()
    return render_template('500.html'), 500
