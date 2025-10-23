from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('crear_entrega/', views.crear_entrega, name='crear_entrega'),
    path('ajax/get_obras/', views.get_obras, name='get_obras'),
    path('crear_empleado/', views.crear_empleado, name='crear_empleado'),
    path('crear_piezas_rechazadas/<int:reporte_id>/', views.crear_piezas_rechazadas, name='crear_piezas_rechazadas'),
    path('detalle_reporte/<int:reporte_id>/', views.detalle_reporte, name='detalle_reporte'),
    path('generar_pdf/<int:reporte_id>/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    path('tabla_reportes/', views.tabla_reportes, name="tabla_reportes"),
    path('ver-imagen/<int:pieza_id>', views.ver_imagen_segura, name='ver_imagen_segura'),
    path('crear_cliente/', views.crear_cliente, name='crear_cliente'),
    path('obras/nueva/', views.crear_obra, name='crear_obra'),
]