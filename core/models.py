from django.db import models
from django.contrib.auth.models import User

# ===================================================================
# MODELOS DE ORGANIZACIÓN Y USUARIOS
# ===================================================================

class Area(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Departamento(models.Model):
    nombre = models.CharField(max_length=100)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='departamentos')

    def __str__(self):
        return f'{self.nombre} ({self.area.nombre})'

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='miembros', null=True, blank=True)

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username

class Jefatura(models.Model):
    trabajador_jefe = models.ForeignKey(User, on_delete=models.PROTECT, related_name='roles_jefatura')
    area_jefatura = models.ForeignKey(Area, on_delete=models.PROTECT)
    departamento_jefatura = models.ForeignKey(Departamento, on_delete=models.PROTECT, null=True, blank=True)
    fecha_inicio_jefatura = models.DateField()
    fecha_fin_jefatura = models.DateField(null=True, blank=True, help_text="Dejar en blanco si la jefatura está activa.")

    def __str__(self):
        return f'Jefatura de {self.trabajador_jefe.username} en {self.area_jefatura.nombre}'


# ===================================================================
# MODELOS DE GESTIÓN DE TICKETS
# ===================================================================

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=25, null=True, blank=True)
    correo_electronico = models.EmailField(max_length=255, unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Ticket(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = 'ABIERTO', 'Abierto'
        EN_PROCESO = 'EN_PROCESO', 'En Proceso'
        RESUELTO = 'RESUELTO', 'Resuelto'
        CERRADO = 'CERRADO', 'Cerrado'
        NO_APLICA = 'NO_APLICA', 'No Aplica'

    class NivelCritico(models.TextChoices):
        BAJO = 'BAJO', 'Bajo'
        MEDIO = 'MEDIO', 'Medio'
        ALTO = 'ALTO', 'Alto'
        CRITICO = 'CRITICO', 'Crítico'

    titulo = models.CharField(max_length=200)
    estado = models.CharField(max_length=50, choices=Estado.choices, default=Estado.ABIERTO)
    descripcion_problema = models.TextField()
    nivel_critico = models.CharField(max_length=50, choices=NivelCritico.choices)
    tipo_problema = models.CharField(max_length=100)
    cliente_solicitante = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='tickets')
    area_asignada = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='tickets_en_area')
    trabajador_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tickets_creados')
    trabajador_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_asignados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Ticket #{self.id}: {self.titulo}'

class Observacion(models.Model):
    ticket_asociado = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='observaciones')
    observacion_texto = models.TextField()
    fecha_hora_observacion = models.DateTimeField(auto_now_add=True)
    autor_trabajador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='observaciones_realizadas')

    def __str__(self):
        return f'Observación en Ticket #{self.ticket_asociado.id} por {self.autor_trabajador.username}'

class Derivacion(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='derivaciones')
    fecha_derivacion = models.DateTimeField(auto_now_add=True)
    area_origen = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='derivaciones_salientes')
    trabajador_origen = models.ForeignKey(User, on_delete=models.PROTECT, related_name='derivaciones_realizadas')
    area_destino = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='derivaciones_entrantes')
    motivo_derivacion = models.TextField()

    def __str__(self):
        return f'Derivación de Ticket #{self.ticket.id} de {self.area_origen.nombre} a {self.area_destino.nombre}'
    
# ===================================================================
# SPRINT 4 - MODELOS DE GESTIÓN ADMINISTRATIVA
# ===================================================================

class Grupo(models.Model):
    """Modelo para agrupar áreas de la organización (HU08)"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(help_text="Descripción del propósito del grupo")
    areas = models.ManyToManyField(Area, related_name='grupos', blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='grupos_creados')
    
    class Meta:
        ordering = ['nombre']
        
    def __str__(self):
        return f'{self.nombre} ({self.areas.count()} áreas)'
    
    def areas_activas(self):
        """Retorna solo las áreas activas del grupo"""
        return self.areas.all()
    
    def puede_eliminar(self):
        """Verifica si el grupo puede ser eliminado"""
        # Por ahora, todos los grupos pueden ser eliminados
        # En el futuro, podría validar si hay procesos dependientes
        return True

class HistorialUsuario(models.Model):
    """Modelo para registrar cambios importantes en usuarios (HU10)"""
    class TipoAccion(models.TextChoices):
        CREACION = 'CREACION', 'Creación'
        ACTIVACION = 'ACTIVACION', 'Activación'
        DESACTIVACION = 'DESACTIVACION', 'Desactivación'
        CAMBIO_ROL = 'CAMBIO_ROL', 'Cambio de Rol'
        CAMBIO_AREA = 'CAMBIO_AREA', 'Cambio de Área'
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_cambios')
    tipo_accion = models.CharField(max_length=20, choices=TipoAccion.choices)
    descripcion = models.TextField()
    fecha_accion = models.DateTimeField(auto_now_add=True)
    realizado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='acciones_realizadas')
    datos_adicionales = models.JSONField(null=True, blank=True, help_text="Información adicional en formato JSON")
    
    class Meta:
        ordering = ['-fecha_accion']
        
    def __str__(self):
        return f'{self.get_tipo_accion_display()} - {self.usuario.username} ({self.fecha_accion.strftime("%d/%m/%Y %H:%M")})'