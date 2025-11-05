from django.contrib import admin
from .models import Categoria, Disponibilidad, CategoriaDano, Rol, Empleado, Cliente, Obras, UsuarioTransportista, Piezas, ReporteDano, PiezaRechazada

# Register your models here.

admin.site.register(Categoria)
admin.site.register(Disponibilidad)
admin.site.register(CategoriaDano)
admin.site.register(Rol)
admin.site.register(Empleado)
admin.site.register(Cliente)
admin.site.register(Obras)
admin.site.register(UsuarioTransportista)
admin.site.register(Piezas)
admin.site.register(ReporteDano)
admin.site.register(PiezaRechazada)