
var obrasUrl = OBRAS_URL; 

$(document).ready(function(){
    $('#id_idCliente').change(function(){
        var cliente_id = $(this).val();
        var obra_select = $('#id_idObra');

        // Lógica de limpieza si no hay cliente seleccionado
        if (!cliente_id) {
            obra_select.empty().append('<option value="">---------</option>');
            return;
        }
        
        $.ajax({
            url: obrasUrl,
            data: {'cliente_id': cliente_id},
            success: function(data){
                obra_select.empty();
                obra_select.append('<option value="">---------</option>');
                
                $.each(data, function(index, obra){
                    obra_select.append('<option value="'+obra.idObra+'">'+obra.nombreObra+'</option>');
                });
            }
        });
    });
});


document.addEventListener("DOMContentLoaded", function() {
            // Selecciona todos los campos de formulario: input, select, textarea
            const formFields = document.querySelectorAll(
                '#id_remitoRecepcion, #id_idEmpleado, #id_idCliente, #id_idObra, ' +
                '#id_nombreConductor, #id_apellidoConductor, #id_patenteConductor, #id_transporteConductor'
            );
            
            // Aplica las clases de estilo de Tailwind a cada campo
            formFields.forEach(field => {
                // Solo agrega las clases si no están ya presentes (útil si usas widget_tweaks)
                if (!field.classList.contains('border')) {
                    field.classList.add(
                        'w-full', 'border', 'border-black/20', 'rounded-md', 'p-2', 'text-sm', 'focus:border-brand', 
                        'focus:ring-brand', 'outline-none', 'transition-colors'
                    );
                }
            });
        });

        