from django.contrib import admin
from .models import Area, Departamento, Perfil, Jefatura, Cliente, Ticket, Observacion, Derivacion, Grupo, HistorialUsuario

# Registrar modelos del Sprint 1-3
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'area']
    list_filter = ['area']
    search_fields = ['nombre']

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'area']
    list_filter = ['area']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name']

@admin.register(Jefatura)
class JefaturaAdmin(admin.ModelAdmin):
    list_display = ['trabajador_jefe', 'area_jefatura', 'fecha_inicio_jefatura', 'fecha_fin_jefatura']
    list_filter = ['area_jefatura', 'fecha_fin_jefatura']
    date_hierarchy = 'fecha_inicio_jefatura'

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'correo_electronico', 'telefono', 'fecha_registro']
    search_fields = ['nombre', 'correo_electronico']
    date_hierarchy = 'fecha_registro'

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'titulo', 'estado', 'nivel_critico', 'area_asignada', 'trabajador_asignado', 'fecha_creacion']
    list_filter = ['estado', 'nivel_critico', 'area_asignada', 'fecha_creacion']
    search_fields = ['titulo', 'descripcion_problema']
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']

@admin.register(Observacion)
class ObservacionAdmin(admin.ModelAdmin):
    list_display = ['ticket_asociado', 'autor_trabajador', 'fecha_hora_observacion']
    list_filter = ['fecha_hora_observacion']
    search_fields = ['observacion_texto']
    date_hierarchy = 'fecha_hora_observacion'

@admin.register(Derivacion)
class DerivacionAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'area_origen', 'area_destino', 'trabajador_origen', 'fecha_derivacion']
    list_filter = ['area_origen', 'area_destino', 'fecha_derivacion']
    date_hierarchy = 'fecha_derivacion'

# SPRINT 4 - Nuevos modelos
@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'cantidad_areas', 'creado_por', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    filter_horizontal = ['areas']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    def cantidad_areas(self, obj):
        return obj.areas.count()
    cantidad_areas.short_description = 'Áreas'

@admin.register(HistorialUsuario)
class HistorialUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo_accion', 'realizado_por', 'fecha_accion']
    list_filter = ['tipo_accion', 'fecha_accion']
    search_fields = ['usuario__username', 'descripcion', 'realizado_por__username']
    date_hierarchy = 'fecha_accion'
    readonly_fields = ['fecha_accion', 'datos_adicionales']
    
    def has_add_permission(self, request):
        # No permitir crear registros manualmente
        return False
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar registros de historial
        return False