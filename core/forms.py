from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Ticket, Cliente, Area, Derivacion, Observacion
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

# SPRINT 2 - NUEVOS FORMULARIOS

class DerivacionForm(forms.ModelForm):
    """Formulario para derivar tickets entre áreas (HU02)"""
    class Meta:
        model = Derivacion
        fields = ['area_destino', 'motivo_derivacion']
        widgets = {
            'area_destino': forms.Select(attrs={'class': 'form-control'}),
            'motivo_derivacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explique el motivo de la derivación...'
            }),
        }
        labels = {
            'area_destino': 'Derivar a área',
            'motivo_derivacion': 'Motivo de derivación'
        }
    
    def __init__(self, *args, **kwargs):
        # Recibir el ticket para excluir el área actual
        self.ticket = kwargs.pop('ticket', None)
        super().__init__(*args, **kwargs)
        
        if self.ticket:
            # Excluir el área actual del ticket
            self.fields['area_destino'].queryset = Area.objects.exclude(
                id=self.ticket.area_asignada.id
            )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que el ticket esté en estado ABIERTO
        if self.ticket and self.ticket.estado != Ticket.Estado.ABIERTO:
            raise forms.ValidationError(
                'Solo se pueden derivar tickets en estado ABIERTO'
            )
        
        return cleaned_data

class ObservacionForm(forms.ModelForm):
    """Formulario para agregar observaciones a tickets (HU04)"""
    class Meta:
        model = Observacion
        fields = ['observacion_texto']
        widgets = {
            'observacion_texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escriba su observación aquí...',
                'maxlength': 1000
            }),
        }
        labels = {
            'observacion_texto': 'Observación'
        }
    
    def clean_observacion_texto(self):
        texto = self.cleaned_data.get('observacion_texto')
        
        # Validar longitud mínima
        if texto and len(texto.strip()) < 10:
            raise forms.ValidationError(
                'La observación debe tener al menos 10 caracteres'
            )
        
        # Validar longitud máxima
        if texto and len(texto) > 1000:
            raise forms.ValidationError(
                'La observación no puede exceder los 1000 caracteres'
            )
        
        return texto.strip()

class CambioEstadoForm(forms.Form):
    """Formulario para cambiar el estado de un ticket (HU03)"""
    ESTADOS_PERMITIDOS = [
        (Ticket.Estado.EN_PROCESO, 'En Proceso'),
        (Ticket.Estado.RESUELTO, 'Resuelto'),
        (Ticket.Estado.NO_APLICA, 'No Aplica'),
        (Ticket.Estado.CERRADO, 'Cerrado'),
    ]
    
    nuevo_estado = forms.ChoiceField(
        choices=ESTADOS_PERMITIDOS,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nuevo estado'
    )
    
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observación sobre el cambio de estado...'
        }),
        label='Observación'
    )
    
    def __init__(self, *args, **kwargs):
        self.ticket = kwargs.pop('ticket', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar estados según el estado actual
        if self.ticket:
            estados_validos = self._get_estados_validos()
            self.fields['nuevo_estado'].choices = [
                (estado, label) for estado, label in self.ESTADOS_PERMITIDOS
                if estado in estados_validos
            ]
    
    def _get_estados_validos(self):
        """Determina qué estados son válidos según el estado actual"""
        estado_actual = self.ticket.estado
        
        if estado_actual == Ticket.Estado.ABIERTO:
            return [Ticket.Estado.EN_PROCESO, Ticket.Estado.NO_APLICA]
        elif estado_actual == Ticket.Estado.EN_PROCESO:
            return [Ticket.Estado.RESUELTO, Ticket.Estado.NO_APLICA]
        elif estado_actual == Ticket.Estado.RESUELTO:
            return [Ticket.Estado.CERRADO]
        else:
            return []
    
    def clean(self):
        cleaned_data = super().clean()
        nuevo_estado = cleaned_data.get('nuevo_estado')
        observacion = cleaned_data.get('observacion')
        
        # Validar transición de estado
        if self.ticket and nuevo_estado:
            estados_validos = self._get_estados_validos()
            if nuevo_estado not in estados_validos:
                raise forms.ValidationError(
                    f'No se puede cambiar de {self.ticket.get_estado_display()} a {dict(self.ESTADOS_PERMITIDOS)[nuevo_estado]}'
                )
        
        # Observación obligatoria para estados finales
        if nuevo_estado in [Ticket.Estado.RESUELTO, Ticket.Estado.NO_APLICA, Ticket.Estado.CERRADO]:
            if not observacion or len(observacion.strip()) < 10:
                raise forms.ValidationError({
                    'observacion': 'La observación es obligatoria para estados finales (mínimo 10 caracteres)'
                })
        
        return cleaned_data