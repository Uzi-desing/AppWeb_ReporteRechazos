from django.db import models
from .storage_backends import AzureMediaStorage
import uuid

# Create your models here.

class Categoria(models.Model):
    idCategoria = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100)
    
    def __str__(self):
        return self.descripcion
    
class Disponibilidad(models.Model):
    idDisponibilidad = models.AutoField(primary_key=True)
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return 'Disponible' if self.disponible else 'No Disponible'
    
class CategoriaDano(models.Model):
    idCategoriaDano = models.AutoField(primary_key=True)
    motivo = models.CharField(max_length=255)
    
    def __str__(self):
        return self.motivo
    
class Rol(models.Model):
    idRol = models.AutoField(primary_key=True)
    puesto = models.CharField(max_length=255)
    
    def __str__(self):
        return self.puesto
    
class Empleado(models.Model):
    idEmpleado = models.AutoField(primary_key=True)
    idRol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    dni = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f'{self.nombre} {self.apellido}'

class Cliente(models.Model):
    idCliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    domicilio = models.CharField(max_length=255)
    
    def __str__(self):
        return self.nombre
    
class Obras(models.Model):
    idObra = models.AutoField(primary_key=True)
    idCliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    nombreObra = models.CharField(max_length=255)
    
    def __str__(self):
        return self.nombreObra
    
class UsuarioTransportista(models.Model):
    idConductor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    patente = models.CharField(max_length=50)
    transporte = models.CharField(max_length=255)
    
    def __str__(self):
        return f'{self.nombre} {self.apellido}'
    
class Piezas(models.Model):
    idPieza = models.AutoField(primary_key=True)
    idDisponibilidad = models.ForeignKey(Disponibilidad, on_delete=models.CASCADE)
    idCategoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    medidas = models.CharField(max_length=100)
    
    def __str__(self):
        return f'{self.idCategoria.descripcion} {self.medidas}'
    
class ReporteDano(models.Model):
    idReporte = models.AutoField(primary_key=True)
    idEmpleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    idCliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    idConductor = models.ForeignKey(UsuarioTransportista, on_delete=models.CASCADE)
    idObra = models.ForeignKey(Obras, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    remitoRecepcion = models.CharField(max_length=255, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.remitoRecepcion:
            self.remitoRecepcion = str(uuid.uuid4())
        
        super().save(*args, **kwargs)    
    
    def __str__(self):
        return f'Reporte de Daño {self.idReporte}'
    
class PiezaRechazada(models.Model):
    idPiezaRechazada = models.AutoField(primary_key=True)
    idReporte = models.ForeignKey(ReporteDano, on_delete=models.CASCADE)
    idPieza = models.ForeignKey(Piezas, on_delete=models.CASCADE)
    idCategoriaDano = models.ForeignKey(CategoriaDano, on_delete=models.CASCADE)
    observaciones = models.TextField()
    cantidad = models.IntegerField()
    imagen = models.ImageField(upload_to='piezas_rechazadas/', storage=AzureMediaStorage(), blank=True, null=True)
    
    def __str__(self):
        return f'Pieza Rechazada {self.idPiezaRechazada}'
    
    def save(self, *args, **kwargs):
        print(f"→ PiezaRechazada.save() imagen={self.imagen.name}")
        super().save(*args, **kwargs)
