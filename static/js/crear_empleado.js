function formatDNI(value) {
        // 1. Limpia cualquier carácter que no sea un número.
        let cleaned = ('' + value).replace(/\D/g, ''); 
        
        // 2. Limita a 10 dígitos (por si es DNI, CUIT, o un número de 9/10 dígitos).
        if (cleaned.length > 10) {
            cleaned = cleaned.substring(0, 10);
        }

        // 3. Aplica el formato: Separa de a 3 dígitos desde el final.
        // Utiliza una expresión regular que encuentra grupos de 3 números
        // desde la derecha y les antepone un punto, excluyendo el inicio.
        return cleaned.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
    }
    
    document.addEventListener("DOMContentLoaded", function() {
        // --- Lógica del DNI (Input y Tabla) ---
        const dniInput = document.getElementById('id_dni');

        if (dniInput) {
            dniInput.addEventListener('input', (e) => {
                e.target.value = formatDNI(e.target.value);
            });
            
            document.getElementById('empleadoForm').addEventListener('submit', (e) => {
                dniInput.value = dniInput.value.replace(/\./g, '');
            });
        }
        
        // Aplicar formato a los DNIs en la tabla de listado
        const dniCells = document.querySelectorAll('#tablaEmpleados tbody td[data-dni]');
        dniCells.forEach(cell => {
            const rawDni = cell.getAttribute('data-dni');
            cell.textContent = formatDNI(rawDni);
        });

        
        // --- Lógica de Componente de Selección de Rol ---
        const selectorButton = document.getElementById('rol_selector');
        const dropdownMenu = document.getElementById('rol_dropdown');
        const hiddenInput = document.getElementById('id_idRol');
        const selectedTextSpan = document.getElementById('selected_rol_text');
        const chevronIcon = selectorButton ? selectorButton.querySelector('[data-lucide="chevron-down"]') : null;
        const rolOptions = document.querySelectorAll('.rol-option');
        
        if (selectorButton) {
            selectorButton.addEventListener('click', (e) => {
                e.preventDefault(); 
                const isExpanded = selectorButton.getAttribute('aria-expanded') === 'true';

                document.querySelectorAll('[data-dropdown-toggle]:not([aria-expanded="false"])').forEach(btn => {
                    if (btn !== selectorButton) {
                        const target = document.getElementById(btn.dataset.dropdownToggle);
                        target.classList.add('hidden');
                        btn.setAttribute('aria-expanded', 'false');
                        const icon = btn.querySelector('[data-lucide="chevron-down"]');
                        if (icon) icon.classList.remove('rotate-180');
                    }
                });


                if (isExpanded) {
                    dropdownMenu.classList.add('hidden');
                    selectorButton.setAttribute('aria-expanded', 'false');
                    if (chevronIcon) chevronIcon.classList.remove('rotate-180');
                } else {
                    dropdownMenu.style.top = `${selectorButton.offsetHeight + 4}px`;
                    dropdownMenu.classList.remove('hidden');
                    selectorButton.setAttribute('aria-expanded', 'true');
                    if (chevronIcon) chevronIcon.classList.add('rotate-180');
                }
            });
        }
        
        rolOptions.forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                const text = option.dataset.text;

                dropdownMenu.classList.add('hidden');
                if (selectorButton) selectorButton.setAttribute('aria-expanded', 'false');
                if (chevronIcon) chevronIcon.classList.remove('rotate-180');

                hiddenInput.value = value;
                selectedTextSpan.textContent = text;
                if (selectorButton) selectorButton.dataset.currentValue = value;
            });
        });

        document.addEventListener('click', (e) => {
            if (selectorButton && dropdownMenu && !dropdownMenu.contains(e.target) && !selectorButton.contains(e.target)) {
                dropdownMenu.classList.add('hidden');
                selectorButton.setAttribute('aria-expanded', 'false');
                if (chevronIcon) chevronIcon.classList.remove('rotate-180');
            }
        });
        
        const initialValue = selectorButton ? selectorButton.dataset.currentValue : '';
        if (initialValue) {
            const initialOption = document.querySelector(`.rol-option[data-value="${initialValue}"]`);
            if (initialOption) {
                selectedTextSpan.textContent = initialOption.dataset.text;
            } else {
                 selectedTextSpan.textContent = "Seleccionar Rol"; 
            }
        } else {
            selectedTextSpan.textContent = "Seleccionar Rol"; 
        }


        // --- Lógica de Paginación ---
        const rows = document.querySelectorAll('.empleado-row');
        const rowsPerPage = 5;
        const totalRows = rows.length;
        const totalPages = Math.ceil(totalRows / rowsPerPage);
        let currentPage = 1;

        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');

        function displayPage(page) {
            currentPage = page;
            const start = (page - 1) * rowsPerPage;
            const end = start + rowsPerPage;

            rows.forEach((row, index) => {
                row.style.display = (index >= start && index < end) ? '' : 'none';
            });

            prevButton.disabled = currentPage === 1;
            nextButton.disabled = currentPage === totalPages || totalPages <= 1; 
            pageInfo.textContent = `Página ${totalPages === 0 ? 0 : currentPage} de ${totalPages}`;
        }

        prevButton.addEventListener('click', () => {
            if (currentPage > 1) {
                displayPage(currentPage - 1);
            }
        });

        nextButton.addEventListener('click', () => {
            if (currentPage < totalPages) {
                displayPage(currentPage + 1);
            }
        });

        displayPage(1);

        if (window.lucide) lucide.createIcons();
    });