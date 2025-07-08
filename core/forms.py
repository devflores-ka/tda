from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Ticket, Cliente, Area, Derivacion, Observacion, Perfil, Jefatura, Grupo, HistorialUsuario
from django.contrib.auth.models import User
from django.utils import timezone

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

# SPRINT 3 - NUEVOS FORMULARIOS

class FiltroTicketsForm(forms.Form):
    """Formulario avanzado para filtrar tickets (HU05)"""
    # Búsqueda general
    busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por ID, título o descripción...'
        }),
        label='Búsqueda'
    )
    
    # Filtros de fecha
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Desde'
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Hasta'
    )
    
    # Estado
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + list(Ticket.Estado.choices),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Estado'
    )
    
    # Nivel crítico
    nivel_critico = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + list(Ticket.NivelCritico.choices),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nivel Crítico'
    )
    
    # Tipo de problema
    tipo_problema = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Hardware, Software...'
        }),
        label='Tipo de Problema'
    )
    
    # Área
    area_asignada = forms.ModelChoiceField(
        required=False,
        queryset=Area.objects.all(),
        empty_label='Todas las áreas',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Área'
    )
    
    # Trabajador asignado
    trabajador_asignado = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        empty_label='Todos los trabajadores',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Asignado a'
    )
    
    # Cliente
    cliente = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre o email del cliente...'
        }),
        label='Cliente'
    )
    
    # Ordenamiento
    orden = forms.ChoiceField(
        required=False,
        choices=[
            ('-fecha_creacion', 'Más recientes primero'),
            ('fecha_creacion', 'Más antiguos primero'),
            ('-nivel_critico', 'Mayor criticidad primero'),
            ('nivel_critico', 'Menor criticidad primero'),
            ('titulo', 'Título (A-Z)'),
            ('-titulo', 'Título (Z-A)'),
            ('-fecha_actualizacion', 'Última actualización'),
        ],
        initial='-fecha_creacion',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Ordenar por'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar queryset de trabajadores para mostrar nombre completo
        self.fields['trabajador_asignado'].label_from_instance = lambda obj: obj.get_full_name() or obj.username
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_desde = cleaned_data.get('fecha_desde')
        fecha_hasta = cleaned_data.get('fecha_hasta')
        
        # Validar rango de fechas
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise forms.ValidationError('La fecha desde no puede ser mayor que la fecha hasta')
        
        return cleaned_data

class UsuarioCreacionForm(forms.ModelForm):
    """Formulario para crear nuevos usuarios (HU07)"""
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='La contraseña debe tener al menos 8 caracteres'
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Área asignada',
        help_text='Dejar vacío para usuarios sin área específica'
    )
    es_jefe = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='¿Es jefe de área?',
        help_text='Marcar si el usuario será jefe del área seleccionada'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        }
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_staff': 'Acceso al panel administrativo'
        }
        help_texts = {
            'username': 'Requerido. 150 caracteres o menos. Letras, números y @/./+/-/_ únicamente.',
            'is_staff': 'Permite acceso al panel de administración Django'
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio")
        # Verificar que el email no esté en uso
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        area = cleaned_data.get('area')
        es_jefe = cleaned_data.get('es_jefe')
        
        # Si es jefe, debe tener área asignada
        if es_jefe and not area:
            raise forms.ValidationError({
                'area': 'Debe seleccionar un área si el usuario es jefe'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
            
            # Crear perfil con área
            area = self.cleaned_data.get('area')
            if area:
                Perfil.objects.create(usuario=user, area=area)
            
            # Si es jefe, crear registro de jefatura
            if self.cleaned_data.get('es_jefe') and area:
                Jefatura.objects.create(
                    trabajador_jefe=user,
                    area_jefatura=area,
                    fecha_inicio_jefatura=timezone.now().date()
                )
        
        return user

class UsuarioEdicionForm(forms.ModelForm):
    """Formulario para editar usuarios existentes (HU07)"""
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Área asignada'
    )
    es_jefe = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='¿Es jefe de área?'
    )
    cambiar_password = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='¿Cambiar contraseña?'
    )
    password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    password2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        }
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_active': 'Usuario activo',
            'is_staff': 'Acceso al panel administrativo'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Obtener área actual del perfil
            try:
                perfil = self.instance.perfil
                self.fields['area'].initial = perfil.area
            except Perfil.DoesNotExist:
                pass
            
            # Verificar si es jefe
            jefatura_activa = self.instance.roles_jefatura.filter(
                fecha_fin_jefatura__isnull=True
            ).first()
            if jefatura_activa:
                self.fields['es_jefe'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        cambiar_password = cleaned_data.get('cambiar_password')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if cambiar_password:
            if not password1:
                raise forms.ValidationError({
                    'password1': 'Debe ingresar una nueva contraseña'
                })
            if password1 != password2:
                raise forms.ValidationError({
                    'password2': 'Las contraseñas no coinciden'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            # Actualizar contraseña si se solicitó
            if self.cleaned_data.get('cambiar_password'):
                user.set_password(self.cleaned_data['password1'])
                user.save()
            
            # Actualizar o crear perfil
            area = self.cleaned_data.get('area')
            perfil, created = Perfil.objects.get_or_create(usuario=user)
            perfil.area = area
            perfil.save()
            
            # Gestionar jefatura
            es_jefe = self.cleaned_data.get('es_jefe')
            jefaturas_activas = user.roles_jefatura.filter(fecha_fin_jefatura__isnull=True)
            
            if es_jefe and area and not jefaturas_activas.exists():
                # Crear nueva jefatura
                Jefatura.objects.create(
                    trabajador_jefe=user,
                    area_jefatura=area,
                    fecha_inicio_jefatura=timezone.now().date()
                )
            elif not es_jefe and jefaturas_activas.exists():
                # Finalizar jefaturas activas
                jefaturas_activas.update(fecha_fin_jefatura=timezone.now().date())

            # AÑADIR: Registrar cambios en historial
            if commit and self.instance.pk:
                user_before = User.objects.get(pk=self.instance.pk)
        
            # Detectar desactivación
            if user_before.is_active and not self.cleaned_data.get('is_active'):
                from .models import HistorialUsuario
                HistorialUsuario.objects.create(
                    usuario=self.instance,
                    tipo_accion=HistorialUsuario.TipoAccion.DESACTIVACION,
                    descripcion='Usuario desactivado desde el panel de edición',
                    realizado_por=self.current_user if hasattr(self, 'current_user') else self.instance,
                    datos_adicionales={
                        'tickets_asignados': self.instance.tickets_asignados.filter(estado__in=['ABIERTO', 'EN_PROCESO']).count()
                    }
                )
        
            # Detectar reactivación
            elif not user_before.is_active and self.cleaned_data.get('is_active'):
                from .models import HistorialUsuario
                HistorialUsuario.objects.create(
                    usuario=self.instance,
                    tipo_accion=HistorialUsuario.TipoAccion.ACTIVACION,
                    descripcion='Usuario reactivado desde el panel de edición',
                    realizado_por=self.current_user if hasattr(self, 'current_user') else self.instance
                )
        
        return user
    
# SPRINT 4 - FORMULARIOS DE GESTIÓN ADMINISTRATIVA

class GrupoForm(forms.ModelForm):
    """Formulario para crear/editar grupos (HU08)"""
    areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Áreas del grupo',
        help_text='Seleccione las áreas que pertenecen a este grupo'
    )
    
    class Meta:
        model = Grupo
        fields = ['nombre', 'descripcion', 'areas', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Grupo Tecnología'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el propósito de este grupo...'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre': 'Nombre del grupo',
            'descripcion': 'Descripción',
            'activo': 'Grupo activo'
        }
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        
        # Validar unicidad considerando la instancia actual
        qs = Grupo.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError('Ya existe un grupo con este nombre')
        
        return nombre
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar la representación de las áreas
        self.fields['areas'].label_from_instance = lambda obj: f"{obj.nombre} ({obj.miembros.count()} miembros)"

class DesactivacionUsuarioForm(forms.Form):
    """Formulario para desactivar usuarios con motivo (HU10)"""
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explique el motivo de la desactivación...'
        }),
        label='Motivo de desactivación',
        help_text='Este motivo quedará registrado en el historial'
    )
    
    confirmar = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Confirmo que deseo desactivar este usuario',
        error_messages={
            'required': 'Debe confirmar la desactivación'
        }
    )
    
    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo')
        if motivo and len(motivo.strip()) < 10:
            raise forms.ValidationError('El motivo debe tener al menos 10 caracteres')
        return motivo.strip()

class AsignacionTicketForm(forms.Form):
    """Formulario para asignar tickets a trabajadores"""
    trabajador_asignado = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label='-- Sin asignar --',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Asignar a'
    )
    
    def __init__(self, *args, **kwargs):
        area = kwargs.pop('area', None)
        super().__init__(*args, **kwargs)
        
        if area:
            # Solo mostrar trabajadores del área
            self.fields['trabajador_asignado'].queryset = User.objects.filter(
                perfil__area=area,
                is_active=True
            ).order_by('first_name', 'last_name', 'username')
            
            # Personalizar etiquetas
            self.fields['trabajador_asignado'].label_from_instance = (
                lambda obj: obj.get_full_name() or obj.username
            )