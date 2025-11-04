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
        response['Content-Disposition'] = f'attachment; filename=Reporte_ECVA_{reporte.idReporte}.pdf'
        buffer = BytesIO()
        
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # ========== ENCABEZADO ==========
        # Rectángulos del header
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.5)
        
        # Rectángulo izquierdo - "DOCUMENTOS DEL SIG"
        c.rect(50, height - 100, 150, 50)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, height - 70, "DOCUMENTOS DEL SIG")
        
        # Rectángulo central - Logo ECVA
        c.rect(200, height - 100, 150, 50)
        try:
            # Ajusta la ruta según donde tengas tu logo
            logo_path = 'static/images/logo-ECVA.png'  # o tu ruta
            logo = ImageReader(logo_path)
            c.drawImage(logo, 230, height - 95, width=90, height=40, preserveAspectRatio=True, mask='auto')
        except:
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(275, height - 75, "ECVA")
        
        # Rectángulo derecho - Tipo de documento
        c.rect(350, height - 100, 195, 50)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(447.5, height - 65, "Tipo documento:")
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(447.5, height - 80, "DOCUMENTO OPERATIVO")
        
        # Segunda fila del header
        c.rect(50, height - 130, 495, 30)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, height - 120, "Rechazo de materiales")
        
        
        # ========== DATOS DEL REPORTE ==========
        y = height - 160
        
        # Primera columna de datos
        data_fields = [
            ("OBRA", reporte.idObra.nombreObra),
            ("REMITO DE RECEPCION", reporte.remitoRecepcion),
            ("FECHA", reporte.fecha.strftime('%d/%m/%Y')),
            ("CLIENTE", reporte.idCliente.nombre),
            ("EMPLEADO", f"{reporte.idEmpleado.nombre} {reporte.idEmpleado.apellido}"),
        ]
        
        for label, value in data_fields:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(60, y, label)
            
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.rect(180, y - 5, 150, 18)
            
            c.setFont("Helvetica", 9)
            c.drawString(185, y, str(value) if value else "")
            
            y -= 25
        
        # INFORME No. (en la esquina superior derecha de esta sección)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(400, height - 160, "INFORME No.")
        c.rect(480, height - 165, 60, 18)
        c.setFont("Helvetica", 10)
        c.drawCentredString(510, height - 160, str(reporte.idReporte))
        
        y -= 20
        
        # ========== SECCIONES DE PIEZAS RECHAZADAS ==========
        c.setFont("Helvetica-Bold", 10)
        
        for idx, pieza in enumerate(piezasRechazadas, 1):
            # Verificar si necesitamos nueva página
            if y < 250:
                c.showPage()
                y = height - 80
            
            # Header de sección: SOPORTE | MOTIVO
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            
            # SOPORTE
            c.rect(50, y - 5, 230, 20, fill=1, stroke=1)
            c.setFillColor(colors.lightgrey)
            c.rect(50, y - 5, 230, 20, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(165, y, "SOPORTE")
            
            # MOTIVO
            c.setFillColor(colors.lightgrey)
            c.rect(280, y - 5, 265, 20, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawCentredString(412.5, y, "MOTIVO")
            
            y -= 25
            
            # Área de imagen (SOPORTE)
            c.setStrokeColor(colors.black)
            c.rect(50, y - 150, 230, 150)
            
            if pieza.imagen:
                try:
                    sas_url = generar_url_sas(pieza.imagen.name, expira_en_min=3)
                    resp = requests.get(sas_url)
                    resp.raise_for_status()
                    
                    img_data = BytesIO(resp.content)
                    img = ImageReader(img_data)
                    
                    # Dibujar imagen centrada en el cuadro
                    c.drawImage(img, 60, y - 145, width=210, height=140, 
                              preserveAspectRatio=True)
                except Exception as e:
                    c.setFont("Helvetica-Oblique", 9)
                    c.drawString(70, y - 75, f"Error al cargar imagen")
            else:
                c.setFont("Helvetica-Oblique", 9)
                c.drawString(120, y - 75, "(Sin imagen)")
            
            # Área de MOTIVO (checkboxes y datos)
            motivo_y = y
            
            # MATERIAL
            c.setFont("Helvetica-Bold", 9)
            c.drawString(290, motivo_y, "MATERIAL")
            c.rect(360, motivo_y - 5, 180, 18)
            c.setFont("Helvetica", 8)
            pieza_info = f"{pieza.idPieza.idCategoria.descripcion} - {pieza.idPieza.medidas}"
            c.drawString(365, motivo_y, pieza_info)
            
            motivo_y -= 25
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(290, motivo_y, "CANT")
            c.rect(360, motivo_y - 5, 180, 18)
            c.setFont("Helvetica", 8)
            pieza_info = f"{pieza.cantidad} Unidades"
            c.drawString(365, motivo_y, pieza_info)
            
            motivo_y -= 25
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(290, motivo_y, "CAT. DAÑO")
            c.rect(360, motivo_y - 5, 180, 18)
            c.setFont("Helvetica", 8)
            pieza_info = f"{pieza.idCategoriaDano}"
            c.drawString(365, motivo_y, pieza_info)
             
            # Cantidad y observaciones
            motivo_y -= 25
            c.setFont("Helvetica-Bold", 9)
            c.drawString(290, motivo_y, "OBSERVACIONES")
            c.rect(300, motivo_y - 40, 240, 40)
            
            c.setFont("Helvetica", 8)
            obs_text = f"{pieza.observaciones or 'Sin observaciones'}"
            # Dividir texto si es muy largo
            if len(obs_text) > 60:
                c.drawString(310, motivo_y - 15, obs_text[:60])
                c.drawString(310, motivo_y - 25, obs_text[60:120])
            else:
                c.drawString(310, motivo_y - 15, obs_text)
            
            y = motivo_y - 60
            
            # Línea separadora entre piezas
            if idx < len(piezasRechazadas):
                c.setStrokeColor(colors.grey)
                c.setLineWidth(0.5)
                c.line(50, y, width - 50, y)
                y -= 25
        
        # ========== DATOS DEL TRANSPORTE ==========
        if y < 150:
            c.showPage()
            y = height - 80
        
        y -= 30
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.5)
        c.line(50, y, width - 50, y)
        y -= 30
        
        transport_fields = [
            ("TRANSPORTE", reporte.idConductor.transporte.title()),
            ("PATENTE", reporte.idConductor.patente.upper()),
            ("NOMBRE Y APELLIDO", f"{reporte.idConductor.nombre.title()} {reporte.idConductor.apellido.title()}"),
        ]
        
        for label, value in transport_fields:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(60, y, label)
            c.setLineWidth(0.5)
            c.line(180, y - 3, 400, y - 3)
            c.setFont("Helvetica", 9)
            c.drawString(185, y, value)
            y -= 25
        
        
        # Área de firma
        y -= 10
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, y, "FIRMA")
        c.line(60, y - 3, 200, y - 3)
        
        c.setFont("Helvetica", 8)
        c.drawString(280, y + 4 , "FIRMA Y ACLARACIÓN")
        c.drawString(280, y - 3, "CONTROL - RECHAZO")
        c.line(280, y - 5, width - 60, y - 5 )
        
        # Pie de página
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(width / 2, 5, 
                           "Sistema de Reportes de Daños © 2025 - Uso Interno")
        
        # Guardar PDF
        c.showPage()
        c.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error al generar PDF: {e}')
        return redirect('detalle_reporte', reporte_id=reporte_id)