document.addEventListener("DOMContentLoaded", function() {
    const formFields = document.querySelectorAll('#id_nombre, .flex input, .flex textarea, .flex select');
        
    formFields.forEach(field => {
        if (!field.classList.contains('border')) {
            field.classList.add(
                'w-full', 'border', 'border-black/20', 'rounded-md', 'p-2', 'text-sm', 'focus:border-brand', 
                'focus:ring-brand', 'outline-none', 'transition-colors'
            );
        }
    });

    // --- Lógica de Paginación de Clientes ---
    const rows = document.querySelectorAll('.cliente-row');
    const rowsPerPage = 5; // Mostrar 5 clientes por página
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

        prevButton.disabled = currentPage === 1 || totalPages <= 1;
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

    // Inicializar la tabla al cargar
    displayPage(1);

    if (window.lucide) lucide.createIcons();
});