from django.contrib import admin
from .models import Cliente, Obras, UsuarioTransportista, ReporteDano, Piezas, Disponibilidad, Categoria, CategoriaDano, PiezaRechazada
# Register your models here.

admin.site.register(Obras)
admin.site.register(Cliente)
admin.site.register(UsuarioTransportista)
admin.site.register(ReporteDano)
admin.site.register(Piezas)
admin.site.register(Disponibilidad)
admin.site.register(Categoria)
admin.site.register(CategoriaDano)
admin.site.register(PiezaRechazada)