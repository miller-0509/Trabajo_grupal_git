from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from functools import wraps
from datetime import date, datetime
from app.models import Usuario, Producto, Movimiento
from app import db

main = Blueprint('main', __name__)


# ============================================================================
# DECORADORES DE AUTENTICACIÓN Y AUTORIZACIÓN
# ============================================================================

def login_required(f):
    """Decorador que requiere que el usuario esté autenticado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador que requiere que el usuario sea administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('main.login'))
        if session.get('usuario_rol') != 'admin':
            flash('No tienes permisos para acceder a esta sección.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# CONTEXTO GLOBAL - Inyectar datos del usuario en todos los templates
# ============================================================================

@main.before_app_request
def cargar_usuario_actual():
    """Carga los datos del usuario actual en g para uso en templates."""
    g.usuario = None
    if 'usuario_id' in session:
        g.usuario = Usuario.query.get(session['usuario_id'])
        if g.usuario is None:
            # El usuario fue eliminado, limpiar la sesión
            session.clear()


@main.app_context_processor
def inject_usuario():
    """Inyecta el usuario actual en todos los templates."""
    return dict(usuario_actual=getattr(g, 'usuario', None))



# ============================================================================
# RUTAS DE AUTENTICACIÓN (Modelo: Usuario)
# ============================================================================

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión de usuario."""
    # Si ya está autenticado, redirigir al dashboard
    if 'usuario_id' in session:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validaciones
        if not username or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('login.html')

        # Buscar usuario
        usuario = Usuario.query.filter_by(username=username).first()

        if usuario is None or not usuario.check_password(password):
            flash('Usuario o contraseña incorrectos.', 'error')
            return render_template('login.html')

        # Iniciar sesión
        session['usuario_id'] = usuario.id
        session['usuario_username'] = usuario.username
        session['usuario_rol'] = usuario.rol

        flash(f'¡Bienvenido, {usuario.username}!', 'success')
        return redirect(url_for('main.index'))

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
    - Si no hay usuarios en el sistema, permite crear el primer admin sin estar autenticado.
    - En cualquier otro caso, solo un admin autenticado puede registrar usuarios.
    """
    total_usuarios = Usuario.query.count()
    es_primer_usuario = total_usuarios == 0

    # Si no es el primer usuario, solo admin puede registrar
    if not es_primer_usuario:
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para registrar usuarios.', 'error')
            return redirect(url_for('main.login'))
        if session.get('usuario_rol') != 'admin':
            flash('Solo los administradores pueden registrar usuarios.', 'error')
            return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirmar_password = request.form.get('confirmar_password', '')
        rol = request.form.get('rol', 'empleado')

        # Validaciones
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

        # Verificar que el username no exista
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
                flash('¡Cuenta de administrador creada exitosamente! Ahora puedes iniciar sesión.', 'success')
                return redirect(url_for('main.login'))
            else:
                flash(f'Usuario "{username}" creado exitosamente con rol "{rol}".', 'success')
                return redirect(url_for('main.listar_usuarios'))
        except Exception:
            db.session.rollback()
            flash('Error al crear el usuario. Inténtalo de nuevo.', 'error')
            return render_template('registro.html', es_primer_usuario=es_primer_usuario)

    return render_template('registro.html', es_primer_usuario=es_primer_usuario)


# ============================================================================
# RUTAS DE GESTIÓN DE USUARIOS (Modelo: Usuario)
# ============================================================================

@main.route('/usuarios')
@admin_required
def listar_usuarios():
    """Lista todos los usuarios registrados (solo admin)."""
    usuarios = Usuario.query.order_by(Usuario.username).all()
    return render_template('usuarios.html', usuarios=usuarios)


@main.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    """Editar un usuario existente (solo admin)."""
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        rol = request.form.get('rol', 'empleado')
        nueva_password = request.form.get('password', '').strip()

        # Validaciones
        errores = []

        if not username:
            errores.append('El nombre de usuario es obligatorio.')
        elif len(username) < 3:
            errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
        elif len(username) > 80:
            errores.append('El nombre de usuario no puede exceder 80 caracteres.')

        if rol not in ('admin', 'empleado'):
            errores.append('Rol no válido. Debe ser "admin" o "empleado".')

        # Verificar username único (si cambió)
        if username != usuario.username:
            existente = Usuario.query.filter_by(username=username).first()
            if existente:
                errores.append('El nombre de usuario ya está en uso por otro usuario.')

        # No permitir cambiar el rol del último admin
        if usuario.rol == 'admin' and rol != 'admin':
            admin_count = Usuario.query.filter_by(rol='admin').count()
            if admin_count <= 1:
                errores.append('No puedes cambiar el rol del único administrador del sistema.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('usuario_form.html', usuario=usuario)

        # Validar nueva contraseña si se proporcionó
        if nueva_password and len(nueva_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('usuario_form.html', usuario=usuario)

        try:
            usuario.username = username
            usuario.rol = rol
            if nueva_password:
                usuario.set_password(nueva_password)
            db.session.commit()
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
    """Eliminar un usuario del sistema (solo admin)."""
    usuario = Usuario.query.get_or_404(id)

    # No permitir eliminarse a sí mismo
    if usuario.id == session.get('usuario_id'):
        flash('No puedes eliminarte a ti mismo.', 'error')
        return redirect(url_for('main.listar_usuarios'))

    # No permitir eliminar al último admin
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


@main.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Ver y editar el perfil del usuario actual (cambiar contraseña)."""
    usuario = Usuario.query.get_or_404(session['usuario_id'])

    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '')
        nueva_password = request.form.get('password', '').strip()
        confirmar_password = request.form.get('confirmar_password', '').strip()

        # Verificar contraseña actual
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
# RUTA DEL DASHBOARD
# ============================================================================

@main.route('/')
@login_required
def index():
    """Dashboard principal con estadísticas del inventario."""
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

    # Estadísticas adicionales
    total_usuarios = Usuario.query.count()
    total_movimientos = Movimiento.query.count()
    valor_inventario = db.session.query(
        db.func.sum(Producto.precio * Producto.cantidad_stock)
    ).scalar() or 0

    return render_template('index.html',
                           total_productos=total_productos,
                           stock_bajo=stock_bajo,
                           movimientos_hoy=movimientos_hoy,
                           movimientos_recientes=movimientos_recientes,
                           total_usuarios=total_usuarios,
                           total_movimientos=total_movimientos,
                           valor_inventario=valor_inventario)


# ============================================================================
# RUTAS DE PRODUCTOS (Modelo: Producto)
# ============================================================================

@main.route('/productos')
@login_required
def listar_productos():
    """Lista todos los productos del inventario ordenados por nombre."""
    productos = Producto.query.order_by(Producto.nombre).all()
    return render_template('productos.html', productos=productos)


@main.route('/productos/buscar')
@login_required
def buscar_productos():
    """Buscar productos por nombre o categoría con filtros."""
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

    productos = productos_query.order_by(Producto.nombre).all()

    # Obtener todas las categorías únicas para el filtro
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
    """Lista productos con stock bajo (igual o menor al mínimo)."""
    productos = Producto.query.filter(
        Producto.cantidad_stock <= Producto.stock_minimo
    ).order_by(Producto.cantidad_stock.asc()).all()
    return render_template('stock_bajo.html', productos=productos)


@main.route('/productos/agregar', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    """Agregar un nuevo producto al inventario."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        categoria = request.form.get('categoria', '').strip()
        precio_str = request.form.get('precio', '').strip()
        cantidad_stock_str = request.form.get('cantidad_stock', '').strip()
        stock_minimo_str = request.form.get('stock_minimo', '').strip()

        # Validaciones
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
            return render_template('producto_form.html')

        try:
            producto = Producto(
                nombre=nombre,
                categoria=categoria if categoria else None,
                precio=precio,
                cantidad_stock=cantidad_stock,
                stock_minimo=stock_minimo
            )
            db.session.add(producto)
            db.session.commit()
            flash(f'Producto "{nombre}" agregado exitosamente.', 'success')
            return redirect(url_for('main.listar_productos'))
        except Exception:
            db.session.rollback()
            flash('Error al agregar el producto. Inténtalo de nuevo.', 'error')
            return render_template('producto_form.html')

    return render_template('producto_form.html')


@main.route('/productos/<int:id>')
@login_required
def detalle_producto(id):
    """Ver detalle de un producto con su historial de movimientos."""
    producto = Producto.query.get_or_404(id)
    movimientos = Movimiento.query.filter_by(
        producto_id=id
    ).order_by(Movimiento.fecha.desc()).all()
    return render_template('producto_detalle.html',
                           producto=producto,
                           movimientos=movimientos)


@main.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    """Editar un producto existente del inventario."""
    producto = Producto.query.get_or_404(id)

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        categoria = request.form.get('categoria', '').strip()
        precio_str = request.form.get('precio', '').strip()
        cantidad_stock_str = request.form.get('cantidad_stock', '').strip()
        stock_minimo_str = request.form.get('stock_minimo', '').strip()

        # Validaciones
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
            producto.categoria = categoria if categoria else None
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
    producto = Producto.query.get_or_404(id)

    try:
        nombre = producto.nombre
        db.session.delete(producto)
        db.session.commit()
        flash(f'Producto "{nombre}" y sus movimientos eliminados exitosamente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar el producto.', 'error')

    return redirect(url_for('main.listar_productos'))


# ============================================================================
# RUTAS DE MOVIMIENTOS (Modelo: Movimiento)
# ============================================================================

@main.route('/movimientos')
@login_required
def listar_movimientos():
    """Lista todos los movimientos con filtros opcionales por tipo, producto y fecha."""
    tipo_filtro = request.args.get('tipo', '').strip()
    producto_filtro = request.args.get('producto_id', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()

    movimientos_query = Movimiento.query

    # Aplicar filtro por tipo
    if tipo_filtro in ('entrada', 'salida'):
        movimientos_query = movimientos_query.filter_by(tipo=tipo_filtro)

    # Aplicar filtro por producto
    if producto_filtro:
        try:
            movimientos_query = movimientos_query.filter_by(
                producto_id=int(producto_filtro)
            )
        except ValueError:
            pass

    # Aplicar filtro por fecha desde
    if fecha_desde:
        try:
            fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
            movimientos_query = movimientos_query.filter(
                Movimiento.fecha >= fecha_desde_dt
            )
        except ValueError:
            pass

    # Aplicar filtro por fecha hasta (incluye todo el día)
    if fecha_hasta:
        try:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
            movimientos_query = movimientos_query.filter(
                Movimiento.fecha <= fecha_hasta_dt
            )
        except ValueError:
            pass

    movimientos = movimientos_query.order_by(Movimiento.fecha.desc()).all()
    productos = Producto.query.order_by(Producto.nombre).all()

    return render_template('movimientos.html',
                           movimientos=movimientos,
                           productos=productos,
                           tipo_filtro=tipo_filtro,
                           producto_filtro=producto_filtro,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)


@main.route('/movimientos/registrar', methods=['GET', 'POST'])
@login_required
def registrar_movimiento():
    """Registrar un nuevo movimiento de inventario (entrada o salida)."""
    productos = Producto.query.order_by(Producto.nombre).all()
    producto_seleccionado = request.args.get('producto_id', None)

    # Convertir a int para comparación correcta en el template
    if producto_seleccionado is not None:
        try:
            producto_seleccionado = int(producto_seleccionado)
        except (ValueError, TypeError):
            producto_seleccionado = None

    if request.method == 'POST':
        producto_id_str = request.form.get('producto_id', '').strip()
        tipo = request.form.get('tipo', '').strip()
        cantidad_str = request.form.get('cantidad', '').strip()

        # Validaciones
        errores = []
        cantidad = None

        if not producto_id_str:
            errores.append('Debes seleccionar un producto.')

        if tipo not in ('entrada', 'salida'):
            errores.append('El tipo de movimiento debe ser "entrada" o "salida".')

        if not cantidad_str:
            errores.append('La cantidad es obligatoria.')
        else:
            try:
                cantidad = int(cantidad_str)
                if cantidad <= 0:
                    errores.append('La cantidad debe ser mayor a cero.')
            except ValueError:
                errores.append('La cantidad debe ser un número entero válido.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_seleccionado)

        producto = Producto.query.get(int(producto_id_str))
        if producto is None:
            flash('El producto seleccionado no existe.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_seleccionado)

        # Verificar stock suficiente para salidas
        if tipo == 'salida' and cantidad > producto.cantidad_stock:
            flash(
                f'Stock insuficiente. "{producto.nombre}" solo tiene '
                f'{producto.cantidad_stock} unidades disponibles.',
                'error'
            )
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_seleccionado)

        try:
            # Actualizar stock del producto
            if tipo == 'entrada':
                producto.cantidad_stock += cantidad
            else:
                producto.cantidad_stock -= cantidad

            # Crear el registro de movimiento
            movimiento = Movimiento(
                producto_id=producto.id,
                tipo=tipo,
                cantidad=cantidad
            )
            db.session.add(movimiento)
            db.session.commit()

            flash(
                f'Movimiento registrado: {tipo.capitalize()} de {cantidad} '
                f'unidades de "{producto.nombre}".',
                'success'
            )

            # Advertir si el stock quedó bajo después del movimiento
            if producto.esta_bajo_stock():
                flash(
                    f'⚠ Alerta: "{producto.nombre}" tiene stock bajo '
                    f'({producto.cantidad_stock} unidades, mínimo: {producto.stock_minimo}).',
                    'warning'
                )

            return redirect(url_for('main.listar_movimientos'))
        except Exception:
            db.session.rollback()
            flash('Error al registrar el movimiento. Inténtalo de nuevo.', 'error')
            return render_template('movimiento_form.html',
                                   productos=productos,
                                   producto_seleccionado=producto_seleccionado)

    return render_template('movimiento_form.html',
                           productos=productos,
                           producto_seleccionado=producto_seleccionado)


@main.route('/movimientos/<int:id>')
@login_required
def detalle_movimiento(id):
    """Ver detalle completo de un movimiento específico."""
    movimiento = Movimiento.query.get_or_404(id)
    return render_template('movimiento_detalle.html', movimiento=movimiento)


@main.route('/movimientos/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_movimiento(id):
    """Eliminar un movimiento y revertir automáticamente el cambio en el stock."""
    movimiento = Movimiento.query.get_or_404(id)
    producto = Producto.query.get(movimiento.producto_id)

    try:
        # Revertir el efecto del movimiento en el stock del producto
        if producto:
            if movimiento.tipo == 'entrada':
                # Si fue una entrada, restar la cantidad al revertir
                producto.cantidad_stock = max(0, producto.cantidad_stock - movimiento.cantidad)
            elif movimiento.tipo == 'salida':
                # Si fue una salida, devolver la cantidad al revertir
                producto.cantidad_stock += movimiento.cantidad

        db.session.delete(movimiento)
        db.session.commit()
        flash('Movimiento eliminado y stock revertido exitosamente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar el movimiento.', 'error')

    return redirect(url_for('main.listar_movimientos'))


# ============================================================================
# RUTA DE REPORTES
# ============================================================================

@main.route('/reportes')
@login_required
def reportes():
    """Dashboard de reportes con estadísticas completas del inventario."""
    # Estadísticas generales
    total_productos = Producto.query.count()
    total_movimientos = Movimiento.query.count()

    # Productos con stock bajo
    productos_stock_bajo = Producto.query.filter(
        Producto.cantidad_stock <= Producto.stock_minimo
    ).order_by(Producto.cantidad_stock.asc()).all()

    # Valor total del inventario
    valor_inventario = db.session.query(
        db.func.sum(Producto.precio * Producto.cantidad_stock)
    ).scalar() or 0

    # Movimientos del día
    movimientos_hoy = Movimiento.query.filter(
        db.func.date(Movimiento.fecha) == date.today()
    ).count()

    # Total de entradas y salidas
    total_entradas = Movimiento.query.filter_by(tipo='entrada').count()
    total_salidas = Movimiento.query.filter_by(tipo='salida').count()

    # Top 5 productos más movidos
    productos_mas_movidos = db.session.query(
        Producto.nombre,
        db.func.count(Movimiento.id).label('total_movimientos')
    ).join(Movimiento).group_by(Producto.id).order_by(
        db.func.count(Movimiento.id).desc()
    ).limit(5).all()

    # Distribución por categorías
    categorias = db.session.query(
        Producto.categoria,
        db.func.count(Producto.id).label('total')
    ).group_by(Producto.categoria).order_by(
        db.func.count(Producto.id).desc()
    ).all()

    return render_template('reportes.html',
                           total_productos=total_productos,
                           total_movimientos=total_movimientos,
                           productos_stock_bajo=productos_stock_bajo,
                           valor_inventario=valor_inventario,
                           movimientos_hoy=movimientos_hoy,
                           total_entradas=total_entradas,
                           total_salidas=total_salidas,
                           productos_mas_movidos=productos_mas_movidos,
                           categorias=categorias)


# ============================================================================
# MANEJADORES DE ERRORES
# ============================================================================

@main.app_errorhandler(404)
def pagina_no_encontrada(error):
    """Maneja errores 404 - Página no encontrada."""
    return render_template('404.html'), 404


@main.app_errorhandler(500)
def error_servidor(error):
    """Maneja errores 500 - Error interno del servidor."""
    db.session.rollback()
    return render_template('500.html'), 500
