document.addEventListener("DOMContentLoaded", function () {
    const buscador = document.getElementById("buscador");
    const fechaDesde = document.getElementById("fechaDesde");
    const fechaHasta = document.getElementById("fechaHasta");
    const btnFiltrar = document.getElementById("filtrarFechas");
    const btnLimpiar = document.getElementById("limpiarFiltros");
    const tablaBody = document.getElementById("tablaBody");
    const filas = Array.from(tablaBody.querySelectorAll("tr"));
    const mensajeNoResultados = document.getElementById("mensajeNoResultados");
    const paginacion = document.getElementById("paginacion");
    const porPagina = 20;
    let paginaActual = 1;
    let filasVisibles = [];

    // Estado de ordenamiento por columna
    const estadoOrden = {};

    // Navegación al detalle
    document.querySelectorAll(".reporte-row").forEach(row => {
        row.addEventListener("click", () => {
            const url = row.getAttribute("data-url");
            if (url) window.location.href = url;
        });
    });

    // ======== FILTROS ========
    function aplicarFiltros() {
        const texto = buscador.value.toLowerCase();
        const desde = fechaDesde.value ? new Date(fechaDesde.value) : null;
        const hasta = fechaHasta.value ? new Date(fechaHasta.value) : null;

        filasVisibles = filas.filter(fila => {
            const celdas = fila.querySelectorAll("td");
            const fechaTexto = celdas[1].textContent.trim();
            const fechaReporte = new Date(fechaTexto);
            let coincide = true;

            if (desde && fechaReporte < desde) coincide = false;
            if (hasta && fechaReporte > hasta) coincide = false;

            if (texto) {
                let coincideTexto = false;
                celdas.forEach(td => {
                    if (td.textContent.toLowerCase().includes(texto)) coincideTexto = true;
                });
                if (!coincideTexto) coincide = false;
            }

            return coincide;
        });

        if (!texto && !desde && !hasta) filasVisibles = [...filas];
        mostrarPagina(1);
    }

    // ======== PAGINACIÓN ========
    function mostrarPagina(pagina) {
        const inicio = (pagina - 1) * porPagina;
        const fin = inicio + porPagina;

        filas.forEach(f => f.style.display = "none");
        filasVisibles.slice(inicio, fin).forEach(f => f.style.display = "");

        paginaActual = pagina;
        renderizarControles();
        mensajeNoResultados.style.display = filasVisibles.length === 0 ? "flex" : "none";
    }

    function renderizarControles() {
        const totalPaginas = Math.ceil(filasVisibles.length / porPagina);
        paginacion.innerHTML = "";
        if (totalPaginas <= 1) return;

        if (paginaActual > 1) {
            const btnPrimera = crearBoton("Primera", () => mostrarPagina(1));
            const btnAnterior = crearBoton("Anterior", () => mostrarPagina(paginaActual - 1));
            paginacion.append(btnPrimera, btnAnterior);
        }

        const info = document.createElement("span");
        info.textContent = `Página ${paginaActual} de ${totalPaginas}`;
        info.className = "px-3 py-1 border rounded bg-black/5 font-medium";
        paginacion.appendChild(info);

        if (paginaActual < totalPaginas) {
            const btnSiguiente = crearBoton("Siguiente", () => mostrarPagina(paginaActual + 1));
            const btnUltima = crearBoton("Última", () => mostrarPagina(totalPaginas));
            paginacion.append(btnSiguiente, btnUltima);
        }
    }

    function crearBoton(texto, accion) {
        const btn = document.createElement("button");
        btn.textContent = texto;
        btn.className = "px-3 py-1 border rounded hover:bg-black/10";
        btn.addEventListener("click", accion);
        return btn;
    }

    buscador.addEventListener("input", aplicarFiltros);
    btnFiltrar.addEventListener("click", aplicarFiltros);
    btnLimpiar.addEventListener("click", () => {
        buscador.value = "";
        fechaDesde.value = "";
        fechaHasta.value = "";
        aplicarFiltros();
    });

    aplicarFiltros();

    // ======== ORDENAMIENTO MEJORADO ========
    const thOrdenables = document.querySelectorAll("th[data-ordenable]");
    
    function actualizarIndicadores(thActivo, asc) {
        document.querySelectorAll(".sort-indicator").forEach(indicator => {
            indicator.textContent = "⇅";
            indicator.classList.remove("text-brand");
            indicator.classList.add("text-black/40");
        });
        
        const indicador = thActivo.querySelector(".sort-indicator");
        if (indicador) {
            indicador.textContent = asc ? "↑" : "↓";
            indicador.classList.remove("text-black/40");
            indicador.classList.add("text-brand");
        }
    }

    thOrdenables.forEach(th => {
        const colIndex = parseInt(th.getAttribute("data-col-index"));
        estadoOrden[colIndex] = true;
        
        th.addEventListener("click", () => {
            const asc = estadoOrden[colIndex];
            
            filasVisibles.sort((a, b) => {
                const textoA = a.querySelectorAll("td")[colIndex].textContent.trim().toLowerCase();
                const textoB = b.querySelectorAll("td")[colIndex].textContent.trim().toLowerCase();

                const numA = parseFloat(textoA);
                const numB = parseFloat(textoB);
                
                if (!isNaN(numA) && !isNaN(numB)) {
                    return asc ? numA - numB : numB - numA;
                } else {
                    return asc ? textoA.localeCompare(textoB) : textoB.localeCompare(textoA);
                }
            });
            
            estadoOrden[colIndex] = !asc;
            actualizarIndicadores(th, asc);
            mostrarPagina(1);
        });
    });
});