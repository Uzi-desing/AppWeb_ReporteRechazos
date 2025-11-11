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
from .models import UsuarioTransportista, Obras, ReporteDano, PiezaRechazada, Empleado, Cliente, Piezas
from django.http import JsonResponse
import uuid, os
from io import BytesIO
from django.db.models import Count, Sum


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
    total_danadas_dict = PiezaRechazada.objects.aggregate(Sum('cantidad'))
    totalPiezas = total_danadas_dict.get('cantidad__sum') or 0
    ultimoReporte = ReporteDano.objects.last()
    
    cliente_mas_reportes_query = ReporteDano.objects \
        .values('idCliente') \
        .annotate(num_reportes=Count('idCliente')) \
        .order_by('-num_reportes') \
        .first()
        
    cliente_mas_reportes = None
    if cliente_mas_reportes_query:
        cliente_id = cliente_mas_reportes_query['idCliente']
        cliente_obj = Cliente.objects.get(pk=cliente_id)
        
        cliente_mas_reportes = {
            'nombre': cliente_obj.nombre,
            'total_reportes': cliente_mas_reportes_query['num_reportes']
        }

   
    ultimoReporte = ReporteDano.objects.last()
    
    context = {
        'reporte': ultimoReporte,
        'total_piezas': totalPiezas,
        'cliente_mas_reportes': cliente_mas_reportes
    }
        
    return render(request, 'home.html', context)

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
        
        # Márgenes
        margin_left = 40
        margin_right = width - 40
        margin_top = height - 50
        
        # ========== FUNCIÓN AUXILIAR PARA NUEVA PÁGINA ==========
        def crear_encabezado(canvas_obj, y_pos):
            """Crea el encabezado en cada página"""
            c.setStrokeColor(colors.HexColor('#000000'))
            c.setLineWidth(1.5)
            
            # Rectángulo izquierdo - "DOCUMENTOS DEL SIG"
            c.rect(margin_left, y_pos - 50, 145, 50)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(margin_left + 72.5, y_pos - 30, "DOCUMENTOS DEL SIG")
            
            # Rectángulo central - Logo ECVA
            logo_x = margin_left + 145
            c.rect(logo_x, y_pos - 50, 150, 50)
            try:
                logo_path = 'static/images/logo-ECVA.png'
                logo = ImageReader(logo_path)
                c.drawImage(logo, logo_x + 30, y_pos - 45, 
                          width=90, height=40, 
                          preserveAspectRatio=True, mask='auto')
            except:
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(logo_x + 75, y_pos - 25, "ECVA")
            
            # Rectángulo derecho - Tipo de documento
            doc_x = logo_x + 150
            c.rect(doc_x, y_pos - 50, margin_right - doc_x, 50)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString((doc_x + margin_right) / 2, y_pos - 25, "Tipo documento:")
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString((doc_x + margin_right) / 2, y_pos - 40, "DOCUMENTO OPERATIVO")
            
            # Segunda fila del header - Título del documento
            c.setFillColor(colors.HexColor('#f0f0f0'))
            c.rect(margin_left, y_pos - 80, margin_right - margin_left, 30, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width / 2, y_pos - 65, "RECHAZO DE MATERIALES")
            
            return y_pos - 100
        
        # ========== PRIMERA PÁGINA - ENCABEZADO ==========
        y = crear_encabezado(c, margin_top)
        
        # ========== DATOS DEL REPORTE ==========
        y -= 20
        
        # Contenedor principal de información
        c.setStrokeColor(colors.HexColor('#cccccc'))
        c.setLineWidth(0.5)
        
        # INFORME No. (destacado en la esquina superior derecha)
        info_box_x = margin_right - 140
        c.setFillColor(colors.HexColor('#fe2020'))
        c.rect(info_box_x, y - 5, 140, 30, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(info_box_x + 10, y + 12, "INFORME No.")
        c.setFont("Helvetica-Bold", 16)
        c.drawString(info_box_x + 10, y - 2, str(reporte.idReporte))
        c.setFillColor(colors.black)
        
        # Grid de información del reporte
        y -= 15
        data_fields = [
            ("OBRA:", reporte.idObra.nombreObra if reporte.idObra else "N/A"),
            ("CLIENTE:", reporte.idCliente.nombre if reporte.idCliente else "N/A"),
            ("FECHA:", reporte.fecha.strftime('%d/%m/%Y')),
            ("REMITO RECEPCIÓN:", reporte.remitoRecepcion or "N/A"),
            ("EMPLEADO:", f"{reporte.idEmpleado.nombre} {reporte.idEmpleado.apellido}" if reporte.idEmpleado else "N/A"),
        ]
        
        box_height = 22
        label_width = 140
        value_width = 300
        
        for label, value in data_fields:
            # Borde del campo
            c.setStrokeColor(colors.HexColor('#e0e0e0'))
            c.setLineWidth(0.5)
            c.rect(margin_left, y - box_height, label_width + value_width, box_height)
            
            # Área del label (con fondo gris claro)
            c.setFillColor(colors.HexColor('#f5f5f5'))
            c.rect(margin_left, y - box_height, label_width, box_height, fill=1, stroke=0)
            
            # Texto del label
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin_left + 8, y - 14, label)
            
            # Texto del valor
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 9)
            # Truncar texto si es muy largo
            max_chars = 50
            display_value = str(value)[:max_chars] + "..." if len(str(value)) > max_chars else str(value)
            c.drawString(margin_left + label_width + 8, y - 14, display_value)
            
            y -= box_height
        
        y -= 30
        
        # ========== SECCIÓN DE PIEZAS RECHAZADAS ==========
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor('#333333'))
        c.drawString(margin_left, y, "DETALLE DE PIEZAS RECHAZADAS")
        y -= 5
        c.setStrokeColor(colors.HexColor('#fe2020'))
        c.setLineWidth(2)
        c.line(margin_left, y, margin_left + 200, y)
        y -= 25
        
        for idx, pieza in enumerate(piezasRechazadas, 1):
            # Verificar espacio disponible (necesitamos ~200 puntos)
            if y < 250:
                c.showPage()
                y = crear_encabezado(c, margin_top)
                y -= 20
            
            # Contenedor de la pieza rechazada
            pieza_height = 180
            c.setStrokeColor(colors.HexColor('#cccccc'))
            c.setLineWidth(1)
            c.rect(margin_left, y - pieza_height, margin_right - margin_left, pieza_height)
            
            # Header de la sección de pieza
            c.setFillColor(colors.HexColor('#f0f0f0'))
            c.rect(margin_left, y - 25, margin_right - margin_left, 25, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin_left + 10, y - 16, f"PIEZA #{idx}")
            
            # Divisor vertical para imagen y datos
            image_width = 240
            divider_x = margin_left + image_width
            c.setStrokeColor(colors.HexColor('#e0e0e0'))
            c.line(divider_x, y - 25, divider_x, y - pieza_height)
            
            # ===== ÁREA DE IMAGEN (IZQUIERDA) =====
            image_box_y = y - 35
            image_box_height = pieza_height - 35
            
            if pieza.imagen:
                try:
                    # Intentar cargar la imagen desde Azure o ruta local
                    if hasattr(pieza.imagen, 'url'):
                        # Si está en Azure Storage
                        try:
                            sas_url = generar_url_sas(pieza.imagen.name, expira_en_min=3)
                            resp = requests.get(sas_url, timeout=5)
                            resp.raise_for_status()
                            img_data = BytesIO(resp.content)
                        except:
                            # Fallback a URL directa
                            resp = requests.get(pieza.imagen.url, timeout=5)
                            resp.raise_for_status()
                            img_data = BytesIO(resp.content)
                        
                        img = ImageReader(img_data)
                        
                        # Calcular dimensiones manteniendo aspecto
                        img_draw_width = image_width - 20
                        img_draw_height = image_box_height - 10
                        
                        c.drawImage(img, 
                                  margin_left + 10, 
                                  y - pieza_height + 10,
                                  width=img_draw_width, 
                                  height=img_draw_height,
                                  preserveAspectRatio=True,
                                  anchor='c')
                except Exception as e:
                    c.setFont("Helvetica-Oblique", 9)
                    c.setFillColor(colors.HexColor('#999999'))
                    c.drawCentredString(margin_left + image_width / 2, 
                                       y - pieza_height / 2, 
                                       "Error al cargar imagen")
                    c.setFillColor(colors.black)
            else:
                c.setFont("Helvetica-Oblique", 9)
                c.setFillColor(colors.HexColor('#999999'))
                c.drawCentredString(margin_left + image_width / 2, 
                                   y - pieza_height / 2, 
                                   "Sin imagen disponible")
                c.setFillColor(colors.black)
            
            # ===== ÁREA DE DATOS (DERECHA) =====
            data_x = divider_x + 10
            data_y = y - 40
            field_spacing = 28
            
            # Campo: MATERIAL
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.HexColor('#666666'))
            c.drawString(data_x, data_y, "MATERIAL")
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
            material_text = f"{pieza.idPieza.idCategoria.descripcion} - {pieza.idPieza.medidas}" if pieza.idPieza else "N/A"
            # Dividir en dos líneas si es muy largo
            if len(material_text) > 35:
                c.drawString(data_x, data_y - 12, material_text[:35])
                c.drawString(data_x, data_y - 22, material_text[35:70])
                data_y -= field_spacing + 10
            else:
                c.drawString(data_x, data_y - 12, material_text)
                data_y -= field_spacing
            
            # Campo: CANTIDAD
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.HexColor('#666666'))
            c.drawString(data_x, data_y, "CANTIDAD")
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
            c.drawString(data_x, data_y - 12, f"{pieza.cantidad} Unidades")
            data_y -= field_spacing
            
            # Campo: CATEGORÍA DE DAÑO
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.HexColor('#666666'))
            c.drawString(data_x, data_y, "CATEGORÍA DE DAÑO")
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.HexColor('#fe2020'))
            c.drawString(data_x, data_y - 12, str(pieza.idCategoriaDano) if pieza.idCategoriaDano else "N/A")
            c.setFillColor(colors.black)
            data_y -= field_spacing
            
            # Campo: OBSERVACIONES (con borde)
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.HexColor('#666666'))
            c.drawString(data_x, data_y, "OBSERVACIONES")
            
            obs_box_height = 50
            c.setStrokeColor(colors.HexColor('#e0e0e0'))
            c.setLineWidth(0.5)
            c.rect(data_x, data_y - obs_box_height - 5, 
                   margin_right - data_x - 10, obs_box_height)
            
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.black)
            obs_text = pieza.observaciones or "Sin observaciones"
            
            # Dividir observaciones en líneas
            max_width = 45
            words = obs_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line + word) < max_width:
                    current_line += word + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())
            
            obs_y = data_y - 15
            for line in lines[:3]:  # Máximo 3 líneas
                c.drawString(data_x + 5, obs_y, line)
                obs_y -= 12
            
            y -= pieza_height + 15
        
        # ========== DATOS DEL TRANSPORTE ==========
        if y < 180:
            c.showPage()
            y = margin_top - 50
        
        y -= 20
        
        # Título de sección
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor('#333333'))
        c.drawString(margin_left, y, "INFORMACIÓN DEL TRANSPORTE")
        y -= 5
        c.setStrokeColor(colors.HexColor('#fe2020'))
        c.setLineWidth(2)
        c.line(margin_left, y, margin_left + 220, y)
        y -= 25
        
        # Contenedor de transporte
        transport_height = 100
        c.setStrokeColor(colors.HexColor('#cccccc'))
        c.setLineWidth(1)
        c.rect(margin_left, y - transport_height, margin_right - margin_left, transport_height)
        
        y -= 20
        
        if reporte.idConductor:
            transport_fields = [
                ("TRANSPORTE:", reporte.idConductor.transporte.title() if reporte.idConductor.transporte else "N/A"),
                ("PATENTE:", reporte.idConductor.patente.upper() if reporte.idConductor.patente else "N/A"),
                ("CONDUCTOR:", f"{reporte.idConductor.nombre.title()} {reporte.idConductor.apellido.title()}" if reporte.idConductor.nombre else "N/A"),
            ]
            
            for label, value in transport_fields:
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(colors.HexColor('#666666'))
                c.drawString(margin_left + 15, y, label)
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.black)
                c.drawString(margin_left + 120, y, value)
                y -= 22
        else:
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(colors.HexColor('#999999'))
            c.drawString(margin_left + 15, y - 30, "Información de transporte no disponible")
            c.setFillColor(colors.black)
        
        # ========== ÁREA DE FIRMAS ==========
        y -= 50
        
        if y < 120:
            c.showPage()
            y = margin_top - 50
        
        # Título
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor('#333333'))
        c.drawString(margin_left, y, "FIRMAS Y AUTORIZACIONES")
        y -= 50
        
        # Dos columnas de firma
        firma_width = (margin_right - margin_left - 20) / 2
        
        # Firma 1 - Conductor
        c.setStrokeColor(colors.HexColor('#cccccc'))
        c.setLineWidth(0.5)
        c.line(margin_left, y, margin_left + firma_width, y)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor('#666666'))
        c.drawString(margin_left, y - 12, "Firma del Conductor")
        
        # Firma 2 - Control
        firma2_x = margin_left + firma_width + 20
        c.line(firma2_x, y, firma2_x + firma_width, y)
        c.drawString(firma2_x, y - 12, "Firma y Aclaración - Control de Rechazo")
        
        # ========== PIE DE PÁGINA ==========
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(colors.HexColor('#999999'))
        c.drawCentredString(width / 2, 25, 
                           f"Sistema de Reportes de Daños ECVA © 2025 - Documento generado el {reporte.fecha.strftime('%d/%m/%Y')}")
        c.drawCentredString(width / 2, 15, "Para uso interno exclusivo")
        
        # Guardar PDF
        c.showPage()
        c.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    except Exception as e:
        messages.error(request, f'Error al generar PDF: {str(e)}')
        return redirect('detalle_reporte', reporte_id=reporte_id)