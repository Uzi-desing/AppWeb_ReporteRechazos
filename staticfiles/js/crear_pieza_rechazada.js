$(document).ready(function() {
    const $managementForm = $('#id_form-TOTAL_FORMS');
    const $formsetTbody = $('#formset-tbody');
    const $addButton = $('#add-form-row');
    const $emptyTemplate = $('#empty-form-template');

    // Función para añadir nueva fila
    function addFormRow() {
        let totalForms = parseInt($managementForm.val());
        const newRowContent = $emptyTemplate.html();
        const $newRow = $(newRowContent);

        // Reemplazar '__prefix__' por el nuevo índice en el HTML de la nueva fila
        const tempRegex = /__prefix__/g;
        $newRow.html($newRow.html().replace(tempRegex, totalForms));
        $newRow.attr('data-prefix', `form-${totalForms}`);

        // Limpiar inputs del nuevo formulario (Mantenemos la lógica de limpieza solo para la fila nueva)
        $newRow.find(':input').each(function() {
            if ($(this).is(':checkbox')) {
                $(this).prop('checked', false);
            } else if (!$(this).is(':hidden') && !$(this).is(':file')) {
                $(this).val('');
            }
        });

        $formsetTbody.append($newRow);
        // Incrementar TOTAL_FORMS sin reindexar filas existentes
        $managementForm.val(totalForms + 1);
    }

    // Eliminar fila sin reindexar: marcar DELETE si existe; si no, remover y ajustar TOTAL_FORMS si era la última
    $formsetTbody.on('click', '.remove-row', function() {
        if (!confirm("¿Estás seguro de que quieres quitar esta fila?")) return;

        const $row = $(this).closest('.form-row');
        const $deleteInput = $row.find('input[type="checkbox"][name$="-DELETE"]');

        if ($deleteInput.length) {
            $deleteInput.prop('checked', true);
            $row.hide();
        } else {
            const totalForms = parseInt($managementForm.val());
            const isLast = ($row.index() === $formsetTbody.find('.form-row').length - 1);
            $row.remove();
            if (isLast) {
                $managementForm.val(Math.max(0, totalForms - 1));
            }
        }
    });

    // Estilo visual de eliminación
    $formsetTbody.on('change', 'input[type="checkbox"][name$="-DELETE"]', function() {
        const $row = $(this).closest('.form-row');
        $row.toggleClass('table-danger', this.checked);
    });

    // Aplicar estilo al cargar (para formularios preexistentes)
    $('input[type="checkbox"][name$="-DELETE"]:checked').each(function() {
        $(this).closest('.form-row').addClass('table-danger');
    });

    // Botón para añadir fila
    $addButton.on('click', addFormRow);
});