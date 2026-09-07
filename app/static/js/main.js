// Lógica JavaScript del cliente para el sistema de inventario D1

document.addEventListener('DOMContentLoaded', function() {
    // Auto-cerrar mensajes flash después de 5 segundos
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.style.display = 'none';
            }, 300);
        }, 5000);
    });

    // Validación de formularios
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#c33';
                } else {
                    field.style.borderColor = '#e0e0e0';
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Por favor, completa todos los campos requeridos.');
            }
        });
    });

    // Confirmación para acciones destructivas
    const deleteButtons = document.querySelectorAll('.btn-danger');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('¿Estás seguro de que deseas realizar esta acción?')) {
                e.preventDefault();
            }
        });
    });

    // Mejoras en la UX para formularios de autenticación
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const loginButton = document.getElementById('btn-login');

        function updateLoginButton() {
            if (usernameInput.value.trim() && passwordInput.value.trim()) {
                loginButton.disabled = false;
                loginButton.style.opacity = '1';
            } else {
                loginButton.disabled = true;
                loginButton.style.opacity = '0.6';
            }
        }

        usernameInput.addEventListener('input', updateLoginButton);
        passwordInput.addEventListener('input', updateLoginButton);
        updateLoginButton();
    }

    const registroForm = document.getElementById('registro-form');
    if (registroForm) {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirmar_password');
        const registrarButton = document.getElementById('btn-registrar');

        function updateRegistroButton() {
            const username = document.getElementById('username').value.trim();
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            if (username && password && confirmPassword && password === confirmPassword) {
                registrarButton.disabled = false;
                registrarButton.style.opacity = '1';
            } else {
                registrarButton.disabled = true;
                registrarButton.style.opacity = '0.6';
            }
        }

        passwordInput.addEventListener('input', updateRegistroButton);
        confirmPasswordInput.addEventListener('input', updateRegistroButton);
        document.getElementById('username').addEventListener('input', updateRegistroButton);
        updateRegistroButton();
    }

    // Mejoras en tablas - resaltar filas al hacer hover
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(function(row) {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.01)';
        });
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // Animación de entrada para cards del dashboard
    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(function() {
            card.style.transition = 'opacity 0.5s, transform 0.5s';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Funcionalidad de búsqueda en tiempo real (si existe campo de búsqueda)
    const searchInputs = document.querySelectorAll('input[type="search"], input[name="q"]');
    searchInputs.forEach(function(input) {
        let timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                // Aquí se podría agregar lógica de búsqueda AJAX
                console.log('Buscando:', input.value);
            }, 300);
        });
    });

    // Scroll suave para enlaces internos
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Indicador de carga para botones
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const originalText = this.textContent;
            this.textContent = 'Procesando...';
            this.disabled = true;

            // Restaurar después de 3 segundos (como fallback)
            setTimeout(function() {
                button.textContent = originalText;
                button.disabled = false;
            }, 3000);
        });
    });

    // Validación de contraseñas fuertes
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(function(field) {
        field.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;

            if (password.length >= 8) strength++;
            if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
            if (password.match(/\d/)) strength++;
            if (password.match(/[^a-zA-Z\d]/)) strength++;

            // Aquí se podría mostrar un indicador visual de fuerza
            console.log('Fuerza de contraseña:', strength);
        });
    });

    // Manejo de errores de red
    window.addEventListener('offline', function() {
        alert('Sin conexión a internet. Algunas funciones pueden no estar disponibles.');
    });

    window.addEventListener('online', function() {
        console.log('Conexión restaurada');
    });

    // Guardar datos de formularios en localStorage para evitar pérdida de datos
    const formInputs = document.querySelectorAll('form input, form select, form textarea');
    formInputs.forEach(function(input) {
        const key = 'form_' + input.form.id + '_' + input.name;

        // Cargar valor guardado
        const savedValue = localStorage.getItem(key);
        if (savedValue && !input.value) {
            input.value = savedValue;
        }

        // Guardar valor al cambiar
        input.addEventListener('input', function() {
            localStorage.setItem(key, this.value);
        });

        // Limpiar al enviar el formulario
        input.form.addEventListener('submit', function() {
            formInputs.forEach(function(inp) {
                localStorage.removeItem('form_' + inp.form.id + '_' + inp.name);
            });
        });
    });

    console.log('Sistema de inventario D1 - JavaScript cargado correctamente');
});
