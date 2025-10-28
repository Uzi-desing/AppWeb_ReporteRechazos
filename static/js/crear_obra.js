document.addEventListener("DOMContentLoaded", function() {
            // Seleccionar todos los campos de entrada y selección dentro del formulario
            const formFields = document.querySelectorAll(
                'input[type="text"], input[type="number"], input[type="email"], input[type="password"], textarea, select'
            );
            
            formFields.forEach(field => {
                // Aplicar las clases de estilo de Tailwind
                field.classList.add(
                    'w-full', 'border', 'border-black/20', 'rounded-md', 'p-2', 'text-sm', 
                    'focus:border-brand', 'focus:ring-brand', 'outline-none', 'transition-colors', 'mt-1'
                );
            });
            
            // Estilizar las etiquetas y los contenedores <p> generados por form.as_p
            const formParagraphs = document.querySelectorAll('.p-6 form > p');
            formParagraphs.forEach(p => {
                p.classList.add('flex', 'flex-col', 'space-y-1', 'mb-4');
                
                // Estilizar la etiqueta
                const label = p.querySelector('label');
                if (label) {
                    label.classList.add('block', 'text-sm', 'font-medium', 'text-black/80');
                }
            });
            
            // Inicializar íconos de Lucide
            if (window.lucide) lucide.createIcons();
        });