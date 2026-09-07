/**
 * INVENTARIO D1 - Scripts JavaScript de la Aplicación
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-desvanecer mensajes flash después de 5 segundos
    const flashMessages = document.querySelectorAll('.flash-messages .alert');
    flashMessages.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // 2. Cálculo dinámico en el formulario de registro de movimiento
    const productoSelect = document.getElementById('producto_id');
    const tipoSelect = document.getElementById('tipo');
    const cantidadInput = document.getElementById('cantidad');

    if (productoSelect && tipoSelect && cantidadInput) {
        const updateStockHint = () => {
            const selectedOption = productoSelect.options[productoSelect.selectedIndex];
            if (!selectedOption || !selectedOption.value) return;

            const text = selectedOption.text;
            const match = text.match(/Stock:\s*(\d+)/i);
            if (match) {
                const stock = parseInt(match[1], 10);
                const cantidad = parseInt(cantidadInput.value || '0', 10);
                const tipo = tipoSelect.value;

                if (tipo === 'salida' && cantidad > stock) {
                    cantidadInput.setCustomValidity(`Stock insuficiente (${stock} disponibles).`);
                } else {
                    cantidadInput.setCustomValidity('');
                }
            }
        };

        productoSelect.addEventListener('change', updateStockHint);
        tipoSelect.addEventListener('change', updateStockHint);
        cantidadInput.addEventListener('input', updateStockHint);
    }
});
