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
from PIL import Image


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
        piezas_rechazadas = PiezaRechazada.objects.filter(idReporte=reporte).select_related(
        'idPieza__idCategoria', 
        'idCategoriaDano'
        )

        for pieza in piezas_rechazadas:
            if pieza.imagen:
                pieza.url_sas = generar_url_sas(pieza.imagen.name)
            else:
                pieza.url_sas = None
            
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
    piezasRechazadas = PiezaRechazada.objects.filter(idReporte=reporte).select_related(
        'idPieza__idCategoria',
        'idCategoriaDano'
    )
    
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
            c.setStrokeColor(colors.HexColor('#000000'))
            c.setLineWidth(1.5)
            c.rect(margin_left, y_pos - 50, 145, 50)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(margin_left + 72.5, y_pos - 30, "DOCUMENTOS DEL SIG")
            
            logo_x = margin_left + 145
            c.rect(logo_x, y_pos - 50, 150, 50)
            try:
                logo_path = os.path.join(settings.STATIC_ROOT, 'images/logo-ECVA.png')
                if not os.path.exists(logo_path):
                    logo_path = 'static/images/logo-ECVA.png'
                logo = ImageReader(logo_path)
                c.drawImage(logo, logo_x + 30, y_pos - 45, width=90, height=40, preserveAspectRatio=True, mask='auto')
            except:
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(logo_x + 75, y_pos - 25, "ECVA")
            
            doc_x = logo_x + 150
            c.rect(doc_x, y_pos - 50, margin_right - doc_x, 50)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString((doc_x + margin_right) / 2, y_pos - 25, "Tipo documento:")
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString((doc_x + margin_right) / 2, y_pos - 40, "DOCUMENTO OPERATIVO")
            
            c.setFillColor(colors.HexColor('#f0f0f0'))
            c.rect(margin_left, y_pos - 80, margin_right - margin_left, 30, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width / 2, y_pos - 65, "RECHAZO DE MATERIALES")
            return y_pos - 100
        
        y = crear_encabezado(c, margin_top)
        
        # ========== DATOS DEL REPORTE ==========
        y -= 20
        c.setStrokeColor(colors.HexColor('#cccccc'))
        c.setLineWidth(0.5)
        
        info_box_x = margin_right - 140
        c.setFillColor(colors.HexColor('#fe2020'))
        c.rect(info_box_x, y - 5, 140, 30, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(info_box_x + 10, y + 12, "INFORME No.")
        c.setFont("Helvetica-Bold", 16)
        c.drawString(info_box_x + 10, y - 2, str(reporte.idReporte))
        
        c.setFillColor(colors.black)
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
        for label, value in data_fields:
            c.setStrokeColor(colors.HexColor('#e0e0e0'))
            c.rect(margin_left, y - box_height, 440, box_height)
            c.setFillColor(colors.HexColor('#f5f5f5'))
            c.rect(margin_left, y - box_height, label_width, box_height, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin_left + 8, y - 14, label)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 9)
            c.drawString(margin_left + label_width + 8, y - 14, str(value)[:55])
            y -= box_height
        
        y -= 30
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, y, "DETALLE DE PIEZAS RECHAZADAS")
        y -= 5
        c.setStrokeColor(colors.HexColor('#fe2020'))
        c.setLineWidth(2)
        c.line(margin_left, y, margin_left + 200, y)
        y -= 25
        
        # ========== BUCLE DE PIEZAS ==========
        for idx, pieza in enumerate(piezasRechazadas, 1):
            if y < 250:
                c.showPage()
                y = crear_encabezado(c, margin_top)
                y -= 20
            
            pieza_height = 180
            c.setStrokeColor(colors.HexColor('#cccccc'))
            c.setLineWidth(1)
            c.rect(margin_left, y - pieza_height, margin_right - margin_left, pieza_height)
            
            c.setFillColor(colors.HexColor('#f0f0f0'))
            c.rect(margin_left, y - 25, margin_right - margin_left, 25, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin_left + 10, y - 16, f"PIEZA #{idx}")
            
            divider_x = margin_left + 240
            c.setStrokeColor(colors.HexColor('#e0e0e0'))
            c.line(divider_x, y - 25, divider_x, y - pieza_height)
            
            # --- PROCESAMIENTO DE IMAGEN ---
            if pieza.imagen:
                try:
                    url_sas = generar_url_sas(pieza.imagen.name, expira_en_min=5)
                    img_response = requests.get(url_sas, timeout=10)
                    
                    if img_response.status_code == 200:
                        # 1. Cargamos la imagen original en Pillow
                        img_temp = Image.open(BytesIO(img_response.content))
                        
                        # 2. REDIMENSIONAMOS (Thumbnail) para ahorrar RAM
                        # Esto reduce la imagen a un tamaño máximo de 800px 
                        # manteniendo la calidad, pero bajando el peso de MB a KB
                        img_temp.thumbnail((800, 800))
                        
                        # 3. Guardamos la imagen optimizada en un nuevo buffer
                        img_optimized = BytesIO()
                        img_temp.save(img_optimized, format='JPEG', quality=75)
                        img_optimized.seek(0)
                        
                        # 4. Ahora sí, se la pasamos a ReportLab
                        img_reader = ImageReader(img_optimized)
                        
                        c.drawImage(img_reader, margin_left + 10, y - pieza_height + 10, 
                                   width=220, height=135, preserveAspectRatio=True, anchor='c')
                    else:
                        raise Exception("No se pudo obtener imagen")
                except Exception as e:
                    c.setFont("Helvetica-Oblique", 7)
                    c.setFillColor(colors.red)
                    c.drawString(margin_left + 10, y - 100, "Error de memoria al procesar imagen")
                    c.setFillColor(colors.black)
            
            # --- DATOS DERECHA ---
            c.setFillColor(colors.black)
            data_x = divider_x + 10
            data_y = y - 40
            c.setFont("Helvetica-Bold", 8)
            c.drawString(data_x, data_y, "MATERIAL")
            c.setFont("Helvetica", 9)
            mat = f"{pieza.idPieza.idCategoria.descripcion} - {pieza.idPieza.medidas}" if pieza.idPieza else "N/A"
            c.drawString(data_x, data_y - 12, mat[:35])
            
            data_y -= 35
            c.setFont("Helvetica-Bold", 8)
            c.drawString(data_x, data_y, "CANTIDAD / DAÑO")
            c.setFont("Helvetica", 9)
            c.drawString(data_x, data_y - 12, f"{pieza.cantidad} Un. - {pieza.idCategoriaDano}")
            
            data_y -= 35
            c.setFont("Helvetica-Bold", 8)
            c.drawString(data_x, data_y, "OBSERVACIONES")
            c.setFont("Helvetica", 8)
            obs = pieza.observaciones or "Sin observaciones"
            c.drawString(data_x, data_y - 12, obs[:45])
            if len(obs) > 45: c.drawString(data_x, data_y - 22, obs[45:90])

            y -= pieza_height + 15

        # ========== SECCIÓN TRANSPORTE Y FIRMAS ==========
        if y < 150:
            c.showPage()
            y = crear_encabezado(c, margin_top)

        y -= 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, y, "INFORMACIÓN DEL TRANSPORTE")
        y -= 30
        if reporte.idConductor:
            c.setFont("Helvetica", 9)
            c.drawString(margin_left + 10, y, f"Transporte: {reporte.idConductor.transporte.upper()}")
            c.drawString(margin_left + 10, y - 15, f"Conductor: {reporte.idConductor.nombre.title()} {reporte.idConductor.apellido.title()}")
            c.drawString(margin_left + 10, y - 30, f"Patente: {reporte.idConductor.patente.upper()}")
        
        y -= 80
        c.line(margin_left, y, margin_left + 150, y)
        c.drawString(margin_left, y - 12, "Firma Conductor")
        c.line(margin_right - 150, y, margin_right, y)
        c.drawString(margin_right - 150, y - 12, "Firma Control ECVA")

        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    
    except Exception as e:
        messages.error(request, f'Error al generar PDF: {str(e)}')
        return redirect('detalle_reporte', reporte_id=reporte_id)