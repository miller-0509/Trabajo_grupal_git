# 🛒 Inventario D1 - Sistema de Gestión de Inventario

Sistema web de gestión de inventario para tiendas tipo D1 desarrollado con **Flask** y **SQLAlchemy**.

---

## 👥 Estructura del Equipo y Roles

El desarrollo está distribuido entre 3 personas con responsabilidades definidas:

| Rol | Responsable | Archivos asignados | Estado inicial |
| :--- | :--- | :--- | :--- |
| **Persona 1** | Modelos & Base de Datos | `app/models.py` | ✅ Generado completo por IA |
| **Persona 2** | Rutas & Lógica de Negocio | `app/routes.py` | 📝 Manual (Blueprint inicial) |
| **Persona 3** | Vistas & Plantillas Jinja2 | `app/templates/*.html`, `app/static/` | 🎨 Manual desde cero |

---

## 📂 Estructura del Proyecto

```text
inventario-d1/
├── app/
│   ├── __init__.py          # Factory de la aplicación y registro de Blueprint
│   ├── models.py            # Modelos de SQLAlchemy (Usuario, Producto, Movimiento)
│   ├── routes.py            # Rutas y lógica de negocio (Persona 2)
│   ├── templates/           # Vistas y plantillas Jinja2 (Persona 3)
│   └── static/              # Archivos estáticos
│       ├── css/
│       │   └── style.css    # Estilos CSS personalizados
│       └── js/
│           └── main.js      # Scripts del cliente
├── config.py                 # Configuración de Flask y SQLite
├── requirements.txt          # Dependencias del proyecto
├── run.py                    # Punto de entrada de la aplicación
├── .gitignore                # Archivos ignorados por Git
└── README.md                 # Documentación del proyecto
```

---

## 🗄️ Modelos de Base de Datos (`app/models.py`)

### 1. `Usuario`
- `id` (Integer, Primary Key)
- `username` (String, único, requerido)
- `password` (String, hash seguro con Werkzeug)
- `rol` (String, ej. `"admin"`, `"empleado"`)
- Métodos: `set_password(password)`, `check_password(password)`

### 2. `Producto`
- `id` (Integer, Primary Key)
- `nombre` (String, requerido)
- `categoria` (String)
- `precio` (Float, requerido)
- `cantidad_stock` (Integer, default `0`)
- `stock_minimo` (Integer, default `5`)
- `fecha_ingreso` (DateTime, default `utcnow`)
- `movimientos` (Relación 1 a N con `Movimiento`)
- Métodos: `esta_bajo_stock()` (retorna `True` si `cantidad_stock <= stock_minimo`)

### 3. `Movimiento`
- `id` (Integer, Primary Key)
- `producto_id` (Integer, Foreign Key a `Producto.id`)
- `tipo` (String: `"entrada"` o `"salida"`)
- `cantidad` (Integer, requerido)
- `fecha` (DateTime, default `utcnow`)
- `producto` (Relación backref con `Producto`)

---

## 🚀 Guía de Inicio Rápido

### 1. Clonar el repositorio y crear entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# En Windows (CMD):
.\venv\Scripts\activate.bat
# En Linux/macOS:
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```bash
python run.py
```

La aplicación iniciará en modo debug en `http://127.0.0.1:5000/`. La base de datos SQLite `inventario.db` se creará automáticamente en la raíz en el primer arranque.

---

## 🌿 Flujo de Trabajo con Git

1. Asegurarse de estar en la rama `develop` actualizada:
   ```bash
   git checkout develop
   git pull origin develop
   ```

2. Crear ramas de trabajo individuales:
   ```bash
   # Persona 2 (Rutas):
   git checkout -b feature/routes-productos

   # Persona 3 (Templates y UI):
   git checkout -b feature/templates-dashboard

   # Persona 1 (Ajustes a modelos si aplica):
   git checkout -b feature/models-ajustes
   ```

3. Realizar commits claros y abrir Pull Request hacia `develop` cuando finalice cada módulo.
