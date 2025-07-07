from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Ticket, Cliente, Area
from django.contrib.auth.models import User

class CustomLoginForm(AuthenticationForm):
    """Formulario de login personalizado"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        }),
        label='Usuario'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label='Contraseña'
    )

class ClienteForm(forms.ModelForm):
    """Formulario para crear/editar clientes"""
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'correo_electronico']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nombre': 'Nombre completo',
            'telefono': 'Teléfono',
            'correo_electronico': 'Correo electrónico'
        }

class TicketForm(forms.ModelForm):
    """Formulario para crear tickets"""
    # Campo para buscar cliente existente
    cliente_existente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Cliente existente',
        empty_label='-- Seleccionar cliente existente --'
    )
    
    # Campos para nuevo cliente
    cliente_nombre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre del cliente'
    )
    cliente_telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Teléfono del cliente'
    )
    cliente_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Email del cliente'
    )
    
    class Meta:
        model = Ticket
        fields = ['titulo', 'descripcion_problema', 'nivel_critico', 
                  'tipo_problema', 'area_asignada']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion_problema': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'nivel_critico': forms.Select(attrs={'class': 'form-control'}),
            'tipo_problema': forms.TextInput(attrs={'class': 'form-control'}),
            'area_asignada': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título del ticket',
            'descripcion_problema': 'Descripción del problema',
            'nivel_critico': 'Nivel de criticidad',
            'tipo_problema': 'Tipo de problema',
            'area_asignada': 'Área asignada'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        cliente_existente = cleaned_data.get('cliente_existente')
        cliente_nombre = cleaned_data.get('cliente_nombre')
        cliente_email = cleaned_data.get('cliente_email')
        
        # Validar que se proporcione un cliente existente o los datos para uno nuevo
        if not cliente_existente and not (cliente_nombre and cliente_email):
            raise forms.ValidationError(
                'Debe seleccionar un cliente existente o proporcionar los datos para uno nuevo.'
            )
        
        return cleaned_data