// Función para ocultar la animación de carga cuando la imagen termina de cargar
    function removeLoadingAnimation(imgElement) {
        const container = document.getElementById(`image-container-${imgElement.dataset.id}`);
        if (container) {
            container.classList.remove('bg-gray-200', 'animate-pulse', 'flex', 'items-center', 'justify-center');
            container.classList.add('h-auto');
            imgElement.classList.remove('hidden');
            // Ocultar el icono de placeholder
            const placeholderIcon = container.querySelector('[data-lucide="image"]');
            if (placeholderIcon) placeholderIcon.style.display = 'none';
        }
    }

    // Función para manejar errores de carga de imagen
    function showImageError(imgElement) {
        const container = document.getElementById(`image-container-${imgElement.dataset.id}`);
        if (container) {
            container.classList.remove('bg-gray-200', 'animate-pulse');
            container.classList.add('bg-red-100', 'border', 'border-red-400');
            container.innerHTML = '<span class="text-xs text-red-600 font-medium p-1">Error al cargar</span>';
        }
    }

    