from django import forms
from django.forms import modelformset_factory
from django.forms.models import BaseModelFormSet
from .models import ReporteDano, Empleado, Obras, UsuarioTransportista, PiezaRechazada, Piezas, CategoriaDano, Cliente, Rol

class ReporteDanoForm(forms.ModelForm):
    idEmpleado = forms.ModelChoiceField(
        queryset=Empleado.objects.all(),
        label='Empleado',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    idCliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label='Cliente',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    idObra = forms.ModelChoiceField(
        queryset=Obras.objects.none(),
        label='Obra',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    nombreConductor = forms.CharField(max_length=255, label='Nombre del Conductor', widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellidoConductor = forms.CharField(max_length=255, label='Apellido del Conductor', widget=forms.TextInput(attrs={'class': 'form-control'}))
    patenteConductor = forms.CharField(max_length=20, label='Patente del Conductor', widget=forms.TextInput(attrs={'class': 'form-control'}))
    transporteConductor = forms.CharField(max_length=255, label='Transporte del Conductor', widget=forms.TextInput(attrs={'class': 'form-control'}))

    remitoRecepcion = forms.CharField(
        label='Remito de Recepción',
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'})
    )

    class Meta:
        model = ReporteDano
        fields = [
            'remitoRecepcion',
            'idEmpleado',
            'idCliente',
            'idObra',
            'nombreConductor',
            'apellidoConductor',
            'patenteConductor',
            'transporteConductor'
        ]

    def __init__(self, *args, **kwargs):
        cliente_id = kwargs.pop('cliente_id', None)
        super().__init__(*args, **kwargs)
        # Solo filtrar obras si hay cliente_id
        if cliente_id:
            self.fields['idObra'].queryset = Obras.objects.filter(idCliente=cliente_id)
        else:
            self.fields['idObra'].queryset = Obras.objects.none()
        
class PiezaRechazadaForm(forms.ModelForm):
    
    idPieza = forms.ModelChoiceField(
        queryset=Piezas.objects.select_related('idCategoria').all(),
        label='Pieza',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    imagen = forms.ImageField(
        required=False, 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['idPieza'].label_from_instance = self.pieza_label_from_instance

    def pieza_label_from_instance(self, obj):
        return f'Categoria: {obj.idCategoria.descripcion} | Medidas: {obj.medidas}'
    
    
    class Meta:
        model = PiezaRechazada
        fields = ['idPieza', 'idCategoriaDano', 'observaciones', 'cantidad', 'imagen']
        labels = {
            'idPieza': 'Pieza',
            'idCategoriaDano': 'Categoría de Daño',
            'observaciones': 'Observaciones',
            'cantidad': 'Cantidad',
            'imagen': 'Imagen'
        }
        widgets = {
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        



PiezaRechazadaFormSet = modelformset_factory(
    PiezaRechazada,
    form=PiezaRechazadaForm,
    extra=1,
    can_delete=True
)

class EmpleadoForm(forms.ModelForm):
    # Definimos el campo de Rol explícitamente para usar un widget específico
    idRol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        label='Rol del Empleado',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Empleado
        fields = ['idRol', 'nombre', 'apellido', 'dni']
        labels = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'dni': 'DNI'
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'dni': forms.TextInput(attrs={'class': 'form-control'})
        }
        

class ClienteForm(forms.ModelForm):
    telefono = forms.RegexField(
        regex=r'^\d+$',
        error_messages={'invalid': 'Solo se permiten números.'}
    )

    class Meta:     
        model = Cliente
        fields = ['idCliente', 'nombre', 'telefono', 'domicilio']
        labels = {
            'nombre': 'Nombre Cliente',
            'telefono': 'Telefono',
            'domicilio': 'Dirección'
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'domicilio': forms.TextInput(attrs={'class': 'form-control'})
        }

class ObrasForm(forms.ModelForm):
    class Meta: 
        model = Obras
        fields = ['idCliente', 'nombreObra']
        labels = {
            'idCliente': 'Cliente',
            'nombreObra': 'Nombre de Obra'
        }
        
        
        
        
    
        
        
        