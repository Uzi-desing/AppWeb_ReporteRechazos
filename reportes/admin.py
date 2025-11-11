from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Categoria, Disponibilidad, CategoriaDano, Rol, Empleado, Cliente, Obras, UsuarioTransportista, Piezas, ReporteDano, PiezaRechazada
from .forms import ReporteDanoForm
import uuid

admin.site.site_header = "Panel de Administración de Reportes"
admin.site.site_title = "Administración de Reportes"
admin.site.index_title = "Gestión de Entregas y Reportes de Daños"


# Register your models here.
@admin.register(ReporteDano)
class ReporteDanoAdmin(ModelAdmin):
    list_display = ('idReporte','idCliente', 'idObra', 'fecha', 'idEmpleado', 'idConductor')
    search_fields = (
    'idReporte',    
    'remitoRecepcion',                     
    'idEmpleado__nombre',          
    'idEmpleado__apellido',        
    'idEmpleado__dni',             
    'idConductor__nombre',         
    'idConductor__apellido',       
    'idConductor__patente',        
    'idObra__nombreObra',)
    list_filter = ('fecha', 'idCliente',)
    readonly_fields = ('remitoRecepcion',)
    list_per_page = 20

    def save_model(self, request, obj, form, change):
        if not obj.remitoRecepcion:
            obj.remitoRecepcion = uuid.uuid4().hex[0:8].upper()        
        return super().save_model(request, obj, form, change)

@admin.register(PiezaRechazada)
class PiezaRechazadaAdmin(ModelAdmin):
    list_display = ('idPiezaRechazada', 'idReporte', 'idPieza', 'idCategoriaDano', 'observaciones', 'cantidad',)
    list_filter = ('idPieza__idCategoria', 'idCategoriaDano__motivo', 'idReporte__idCliente',)
    
@admin.register(Cliente)
class ClienteAdmin(ModelAdmin):
    list_display = ('idCliente', 'nombre', 'telefono', 'domicilio')
    search_fields = ('nombre', 'idCliente',)
    list_per_page = 10
    

@admin.register(Obras)
class ObrasAdmin(ModelAdmin):
    list_display = ('idObra', 'nombreObra', 'idCliente',)
    search_fields = ('nombreObra', 'idCliente__nombre')
    list_filter = ('idCliente',)
    list_per_page = 20

@admin.register(Categoria)
class CategoriaAdmin(ModelAdmin):
    list_display = ('idCategoria', 'descripcion')
    search_fields = ('idCategoria', 'descripcion')
    list_filter = ('descripcion',)
    list_per_page = 10
        
@admin.register(UsuarioTransportista)
class UsuarioTransportistaAdmin(ModelAdmin):
    list_display = ('idConductor', 'nombre', 'apellido', 'patente', 'transporte',)
    search_fields = ('idConductor', 'patente',)
    list_per_page = 10

@admin.register(Rol)
class RolAdmin(ModelAdmin):
    list_display = ('idRol', 'puesto',)
    list_filter = ('puesto',)
    list_per_page = 10

@admin.register(CategoriaDano)
class CategoriaDanoAdmin(ModelAdmin):
    list_display = ('idCategoriaDano', 'motivo',)
    
@admin.register(Piezas)
class PiezaAdmin(ModelAdmin):
    list_display = ('idPieza', 'idCategoria', 'medidas', 'idDisponibilidad',)
    list_filter = ('idCategoria__descripcion', 'medidas',)
    list_per_page = 10
    
@admin.register(Empleado)
class EmpleadoAdmin(ModelAdmin):
    list_display = ('idEmpleado', 'nombre', 'apellido', 'dni', 'idRol')
    search_fields = ('nombre', 'apellido', 'dni',)
    list_filter = ('idRol__puesto',)
    
@admin.register(Disponibilidad)
class DisponibilidadAdmin(ModelAdmin):
    pass
    







