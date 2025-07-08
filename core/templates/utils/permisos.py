from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def es_jefe_o_admin(user):
    """Verifica si el usuario es jefe de área o administrador"""
    if user.is_superuser:
        return True
    
    return user.roles_jefatura.filter(
        fecha_fin_jefatura__isnull=True
    ).exists()

def es_del_area(user, area):
    """Verifica si el usuario pertenece a un área específica"""
    if user.is_superuser:
        return True
    
    if hasattr(user, 'perfil') and user.perfil.area == area:
        return True
    
    return False

def puede_editar_ticket(user, ticket):
    """Verifica si un usuario puede editar un ticket"""
    if user.is_superuser:
        return True
    
    # Creador del ticket
    if user == ticket.trabajador_creador:
        return True
    
    # Asignado al ticket
    if user == ticket.trabajador_asignado:
        return True
    
    # Del área del ticket
    if hasattr(user, 'perfil') and user.perfil.area == ticket.area_asignada:
        return True
    
    # Jefe del área del ticket
    if user.roles_jefatura.filter(
        area_jefatura=ticket.area_asignada,
        fecha_fin_jefatura__isnull=True
    ).exists():
        return True
    
    return False

def requiere_jefe_o_admin(view_func):
    """Decorador que requiere que el usuario sea jefe o admin"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not es_jefe_o_admin(request.user):
            messages.error(request, 'No tienes permisos para acceder a esta sección')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped_view

def requiere_permiso_ticket(view_func):
    """Decorador que verifica permisos sobre un ticket específico"""
    @wraps(view_func)
    def wrapped_view(request, pk, *args, **kwargs):
        from core.models import Ticket
        ticket = Ticket.objects.get(pk=pk)
        
        if not puede_editar_ticket(request.user, ticket):
            messages.error(request, 'No tienes permisos para modificar este ticket')
            return redirect('ver_ticket', pk=pk)
        
        return view_func(request, pk, *args, **kwargs)
    return wrapped_view

class PermisosMixin:
    """Mixin para vistas basadas en clases que requieren permisos especiales"""
    
    def dispatch(self, request, *args, **kwargs):
        if not self.tiene_permiso():
            messages.error(request, 'No tienes permisos para acceder a esta sección')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def tiene_permiso(self):
        """Método a sobrescribir en las subclases"""
        return self.request.user.is_superuser