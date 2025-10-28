from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from .forms import ReporteDanoForm, EmpleadoForm, PiezaRechazadaForm, PiezaRechazadaFormSet, ClienteForm, ObrasForm
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseNotAllowed, Http404
from .models import UsuarioTransportista, Obras, ReporteDano, PiezaRechazada, Empleado, Cliente
from django.http import JsonResponse
import uuid, os
from io import BytesIO


#Librerias para ReporLab y Azure
import requests
from django.utils.text import slugify
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader
from reportes.storage_backends import AzureMediaStorage
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .utils.utils_azure import generar_url_sas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet






# Create your views here.
@never_cache
@login_required
@require_GET
def home(request):
    
    ultimoReporte = ReporteDano.objects.last()
   
    return render(request, 'home.html', {'reporte': ultimoReporte})

@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):

    if request.method == 'GET':
        return render(request, 'login.html', {'loginForm': AuthenticationForm()})
    
    else: 
        usuario = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        
        if usuario is None:
            return render(request, 'login.html', {
                'loginForm': AuthenticationForm(), 'error': 'Contraseña o Usuario incorrecto'
            })
            
        login(request, usuario)
        return redirect('home')
    
@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@require_http_methods(["GET", "POST"])
def crear_entrega(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('idCliente')
        form = ReporteDanoForm(request.POST, cliente_id=cliente_id)
        
        if form.is_valid():
            nombreConductor = form.cleaned_data['nombreConductor'].lower()
            apellidoConductor = form.cleaned_data['apellidoConductor'].lower()
            patenteConductor = form.cleaned_data['patenteConductor']
            transporteConductor = form.cleaned_data['transporteConductor']
            
            conductor, creado = UsuarioTransportista.objects.get_or_create(
                patente=patenteConductor,
                defaults={
                    'nombre': nombreConductor,
                    'apellido': apellidoConductor,
                    'transporte': transporteConductor
                }
            )
            if not creado:
                conductor.nombre = nombreConductor
                conductor.apellido = apellidoConductor
                conductor.transporte = transporteConductor
                conductor.save()
            
            reporte = form.save(commit=False)
            reporte.idConductor = conductor
            reporte.idEmpleado = Empleado.objects.get(idEmpleado=1)
            reporte.remitoRecepcion = form.cleaned_data['remitoRecepcion']
            reporte.save()
            
            messages.success(request, 'Entrega creada con éxito. Ahora registra las piezas rechazadas.')
            return redirect('crear_piezas_rechazadas', reporte_id=reporte.idReporte)
        else:
            print("Errores del formulario:", form.errors)
            messages.error(request, 'Error al crear el reporte. Revisa los datos ingresados.')
    else:
        remitoAutogenerado = str(uuid.uuid4()).split('-')[0].upper()
        form = ReporteDanoForm(initial={'remitoRecepcion': remitoAutogenerado})
    
    return render(request, 'crear_entrega.html', {'form': form})

@login_required
@require_GET
def get_obras(request):
    cliente_id = request.GET.get('cliente_id')
    obras = Obras.objects.filter(idCliente = cliente_id).order_by('nombreObra').values('idObra', 'nombreObra')
    return JsonResponse(list(obras), safe=False)

@login_required
@require_http_methods(["GET", "POST"])
def crear_piezas_rechazadas(request, reporte_id):
    reporte = get_object_or_404(ReporteDano, idReporte=reporte_id)

    # Inicializa el formset con al menos un formulario
    formset = PiezaRechazadaFormSet(
        request.POST or None,
        request.FILES or None,
        queryset=PiezaRechazada.objects.none()
    )

    if request.method == 'POST':        
        if formset.is_valid():
            idx = 0
            for idx, form in enumerate(formset):
               if form.has_changed() and not form.cleaned_data.get('DELETE'):
                   pieza_rechazada = form.save(commit=False)
                   pieza_rechazada.idReporte = reporte
                   pieza_rechazada.save()
            
            messages.success(request, 'Piezas Rechazadas registradas con exito.')
            return redirect('home')
        else:
            messages.error(request, 'Error al guardar. Revisa los datos ingresados.')
            try:
                print('Formset errors:', formset.errors)
            except Exception:
                pass

    return render(request, 'crear_piezas_rechazadas.html', {
        'formset': formset,
        'reporte': reporte
    })
    

@never_cache
@login_required
@require_GET
def detalle_reporte(request, reporte_id):
    
    if request.method == 'GET':
        reporte = get_object_or_404(ReporteDano, idReporte=reporte_id)
        piezas_rechazadas = PiezaRechazada.objects.filter(idReporte=reporte)

            
        return render(request, 'detalle_reporte.html', {
            'reporte': reporte,
            'piezas_rechazadas': piezas_rechazadas,
        })

    return HttpResponseNotAllowed(['GET'])    
    


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def crear_empleado(request):
    empleados = Empleado.objects.all()
    
    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            empleado = form.save(commit=False)
            empleado.nombre = empleado.nombre.lower()
            empleado.apellido = empleado.apellido.lower()
            
            empleado.save()
            
            messages.success(request, '¡Empleado creado con éxito!')
            return redirect('crear_empleado')
    else:
        form = EmpleadoForm()
    
    
    return render(request, 'crear_empleado.html', {'form': form, 'empleados': empleados})


@login_required
@require_http_methods(["GET", "POST"])
def crear_cliente(request):
    
    clientes = Cliente.objects.all()
    
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente creado con exito')
            return redirect('home')
    else: 
        form = ClienteForm()
        
    return render(request, 'crear_cliente.html', {'form': form, 'clientes': clientes})
            
@login_required
@require_http_methods(["GET", "POST"])
def crear_obra(request):
    if request.method == 'POST':
        form = ObrasForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ObrasForm()
    return render (request, 'crear_obra.html', {'form': form})

@never_cache
@login_required
def tabla_reportes(request):
    reportes = ReporteDano.objects.all().order_by('-idReporte')
    
    return render(request, 'tabla_reportes.html', {
        'reportes': reportes,
    })



@login_required
@require_GET
def ver_imagen_segura(request, pieza_id):
    pieza = get_object_or_404(PiezaRechazada, idPiezaRechazada=pieza_id)
    
    if not pieza.imagen:
        raise Http404("Imagen no encontrada")
    
    try:
        url_temporal = generar_url_sas(pieza.imagen.name, expira_en_min=3)
        
        respuesta = requests.get(url_temporal)
        if respuesta.status_code != 200:
            raise Http404("No se pudo obtener la imagen")
        
        content_type = respuesta.headers.get("Content-Type", "image/png")
        return HttpResponse (respuesta.content, content_type=content_type)
    
    except Exception as e:
        print(f"Error al cargar imagen: {e}")
        raise Http404("Error al cargar imagen")



@login_required
@require_GET
def generar_reporte_pdf(request, reporte_id):
    reporte = get_object_or_404(ReporteDano, idReporte=reporte_id)
    piezasRechazadas = PiezaRechazada.objects.filter(idReporte=reporte)
    
    try:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=Reporte{reporte.idReporte}.pdf'
        buffer = BytesIO()
    
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        c.setFillColor(colors.HexColor("#002b36"))
        c.rect(0, height - 80, width, 80, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, height - 50, f"REPORTE DE DAÑOS N° {reporte.idReporte}")

        # 🔹 Datos generales del reporte
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, height - 110, "Datos del Reporte:")

        c.setFont("Helvetica", 11)
        c.drawString(70, height - 130, f"Fecha: {reporte.fecha.strftime('%d/%m/%Y')}")
        c.drawString(70, height - 145, f"Remito Recepción: {reporte.remitoRecepcion}")
        c.drawString(70, height - 160, f"Cliente: {reporte.idCliente.nombre}")
        c.drawString(70, height - 175, f"Obra: {reporte.idObra.nombreObra}")
        c.drawString(70, height - 190, f"Responsable: {reporte.idEmpleado.nombre.title()} {reporte.idEmpleado.apellido.title()}")

        y = height - 220

        # 🔹 Tabla de piezas rechazadas
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Piezas Rechazadas:")
        y -= 20

        if not piezasRechazadas:
            c.setFont("Helvetica-Oblique", 11)
            c.drawString(70, y, "No hay piezas rechazadas registradas para este reporte.")
        else:
            # Datos de tabla
            data = [["Categoría Pieza", "Medida", "Cantidad", "Categoría Daño", "Observaciones"]]
            for p in piezasRechazadas:
                data.append([
                    str(p.idPieza.idCategoria.descripcion),
                    str(p.idPieza.medidas),
                    str(p.cantidad),
                    str(p.idCategoriaDano),
                    (p.observaciones or "Ninguna"),
                ])

            # Estilo y formato
            table = Table(data, colWidths=[100, 90, 60, 100, 120])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#073642")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))

            # Dibujar tabla
            table.wrapOn(c, width, y)
            table_height = table._height
            table.drawOn(c, 50, y - table_height)
            y -= (table_height + 20)

            # 🔹 Imágenes de piezas (si existen)
            for pieza in piezasRechazadas:
                if y < 200:
                    c.showPage()
                    y = height - 100
                    c.setFont("Helvetica-Bold", 13)
                    c.drawString(50, y, "Piezas Rechazadas:")
                    y -= 30

                c.setFont("Helvetica-Bold", 11)
                c.drawString(50, y, f"Pieza: {pieza.idPieza.idCategoria.descripcion} ({pieza.cantidad} u.)")
                y -= 15

                if pieza.imagen:
                    try:
                        sas_url = generar_url_sas(pieza.imagen.name, expira_en_min=3)
                        resp = requests.get(sas_url)
                        resp.raise_for_status()

                        img_data = BytesIO(resp.content)
                        img = ImageReader(img_data)

                        ancho, alto = 180, 120
                        c.drawImage(img, 70, y - alto, width=ancho, height=alto, preserveAspectRatio=True)
                        y -= alto + 20
                    except Exception as e:
                        c.setFont("Helvetica-Oblique", 10)
                        c.drawString(70, y, f"(Error al cargar imagen: {e.__class__.__name__})")
                        y -= 20
                else:
                    c.setFont("Helvetica-Oblique", 10)
                    c.drawString(70, y, "(Sin imagen)")
                    y -= 20

        # 🔹 Datos del chofer
        if y < 180:
            c.showPage()
            y = height - 100

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Datos del Chofer:")
        y -= 25

        c.setFont("Helvetica", 11)
        c.drawString(70, y, f"Transporte: {reporte.idConductor.transporte.title()}")
        y -= 18
        c.drawString(70, y, f"Patente: {reporte.idConductor.patente.upper()}")
        y -= 18
        c.drawString(70, y, f"Nombre y Apellido: {reporte.idConductor.nombre.title()} {reporte.idConductor.apellido.title()}")
        y -= 30
        c.drawString(70, y, "Firma: __________________________")

        # 🔹 Pie de página
        c.setStrokeColor(colors.gray)
        c.line(50, 50, width - 50, 50)
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.gray)
        c.drawCentredString(width / 2, 35, "Sistema de Reportes de Daños © 2025 - Uso Interno")

        
        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
    
        return response

    except Exception as e:
        messages.error(request, f'Error al generar PDF: {e}')
        return redirect ('detalle_reporte', reporte_id=reporte_id)
    

    
    


    
    



