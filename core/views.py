from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import (
    CustomLoginForm, TicketForm, ClienteForm, DerivacionForm, 
    ObservacionForm, CambioEstadoForm, FiltroTicketsForm,
    UsuarioCreacionForm, UsuarioEdicionForm
)
from .models import Ticket, Cliente, Area, Perfil, Jefatura, Derivacion, Observacion

def home_view(request):
    """Vista principal - redirige al login o dashboard según autenticación"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

def login_view(request):
    """Vista de login personalizada"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido {user.get_full_name() or user.username}')
            
            # Redirección basada en rol
            if hasattr(user, 'perfil'):
                # Si es jefe de área, redirigir a dashboard de jefatura
                if user.roles_jefatura.filter(fecha_fin_jefatura__isnull=True).exists():
                    return redirect('dashboard_jefatura')
            
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        form = CustomLoginForm()
    
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    """Vista de logout"""
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente')
    return redirect('login')

@login_required
def dashboard_view(request):
    """Dashboard principal - muestra resumen de tickets"""
    # Obtener estadísticas básicas
    total_tickets = Ticket.objects.count()
    tickets_abiertos = Ticket.objects.filter(estado=Ticket.Estado.ABIERTO).count()
    tickets_en_proceso = Ticket.objects.filter(estado=Ticket.Estado.EN_PROCESO).count()
    tickets_resueltos = Ticket.objects.filter(estado=Ticket.Estado.RESUELTO).count()
    
    # Tickets asignados al usuario actual
    mis_tickets = Ticket.objects.filter(trabajador_asignado=request.user).order_by('-fecha_creacion')[:5]
    
    # Tickets recientes del área del usuario (si tiene perfil con área)
    tickets_area = []
    if hasattr(request.user, 'perfil') and request.user.perfil.area:
        tickets_area = Ticket.objects.filter(
            area_asignada=request.user.perfil.area
        ).order_by('-fecha_creacion')[:5]
    
    context = {
        'total_tickets': total_tickets,
        'tickets_abiertos': tickets_abiertos,
        'tickets_en_proceso': tickets_en_proceso,
        'tickets_resueltos': tickets_resueltos,
        'mis_tickets': mis_tickets,
        'tickets_area': tickets_area,
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def dashboard_jefatura_view(request):
    """Dashboard especial para jefes de área"""
    # Verificar que el usuario sea jefe
    jefaturas_activas = request.user.roles_jefatura.filter(fecha_fin_jefatura__isnull=True)
    if not jefaturas_activas.exists():
        return redirect('dashboard')
    
    # Obtener el área de jefatura
    area_jefatura = jefaturas_activas.first().area_jefatura
    
    # Estadísticas del área
    tickets_area = Ticket.objects.filter(area_asignada=area_jefatura)
    total_area = tickets_area.count()
    abiertos_area = tickets_area.filter(estado=Ticket.Estado.ABIERTO).count()
    en_proceso_area = tickets_area.filter(estado=Ticket.Estado.EN_PROCESO).count()
    resueltos_area = tickets_area.filter(estado=Ticket.Estado.RESUELTO).count()
    
    # Tickets por nivel crítico
    criticos = tickets_area.filter(nivel_critico=Ticket.NivelCritico.CRITICO).count()
    altos = tickets_area.filter(nivel_critico=Ticket.NivelCritico.ALTO).count()
    
    # Trabajadores del área
    trabajadores_area = area_jefatura.miembros.all()
    
    context = {
        'area_jefatura': area_jefatura,
        'total_area': total_area,
        'abiertos_area': abiertos_area,
        'en_proceso_area': en_proceso_area,
        'resueltos_area': resueltos_area,
        'criticos': criticos,
        'altos': altos,
        'trabajadores_area': trabajadores_area,
        'tickets_recientes': tickets_area.order_by('-fecha_creacion')[:10],
    }
    
    return render(request, 'core/dashboard_jefatura.html', context)

@login_required
def crear_ticket_view(request):
    """Vista para crear un nuevo ticket"""
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            # Obtener o crear cliente
            cliente = form.cleaned_data.get('cliente_existente')
            if not cliente:
                # Crear nuevo cliente
                cliente = Cliente.objects.create(
                    nombre=form.cleaned_data['cliente_nombre'],
                    telefono=form.cleaned_data.get('cliente_telefono', ''),
                    correo_electronico=form.cleaned_data['cliente_email']
                )
            
            # Crear ticket
            ticket = form.save(commit=False)
            ticket.cliente_solicitante = cliente
            ticket.trabajador_creador = request.user
            ticket.save()
            
            messages.success(request, f'Ticket #{ticket.id} creado exitosamente')
            return redirect('ver_ticket', pk=ticket.id)
    else:
        form = TicketForm()
    
    return render(request, 'core/crear_ticket.html', {'form': form})

@login_required
def lista_tickets_view(request):
    """Vista de lista de tickets con filtros avanzados y paginación (HU05 mejorada)"""
    # Inicializar formulario de filtros
    form = FiltroTicketsForm(request.GET or None)
    
    # Query base con optimizaciones
    tickets = Ticket.objects.select_related(
        'cliente_solicitante', 
        'area_asignada', 
        'trabajador_creador', 
        'trabajador_asignado'
    ).prefetch_related(
        'observaciones',
        'derivaciones'
    )
    
    # Aplicar filtros si el formulario es válido
    if form.is_valid():
        # Búsqueda general
        busqueda = form.cleaned_data.get('busqueda')
        if busqueda:
            tickets = tickets.filter(
                Q(id__icontains=busqueda) |
                Q(titulo__icontains=busqueda) |
                Q(descripcion_problema__icontains=busqueda)
            )
        
        # Filtro de fechas
        fecha_desde = form.cleaned_data.get('fecha_desde')
        if fecha_desde:
            tickets = tickets.filter(fecha_creacion__date__gte=fecha_desde)
        
        fecha_hasta = form.cleaned_data.get('fecha_hasta')
        if fecha_hasta:
            tickets = tickets.filter(fecha_creacion__date__lte=fecha_hasta)
        
        # Estado
        estado = form.cleaned_data.get('estado')
        if estado:
            tickets = tickets.filter(estado=estado)
        
        # Nivel crítico
        nivel_critico = form.cleaned_data.get('nivel_critico')
        if nivel_critico:
            tickets = tickets.filter(nivel_critico=nivel_critico)
        
        # Tipo de problema
        tipo_problema = form.cleaned_data.get('tipo_problema')
        if tipo_problema:
            tickets = tickets.filter(tipo_problema__icontains=tipo_problema)
        
        # Área
        area_asignada = form.cleaned_data.get('area_asignada')
        if area_asignada:
            tickets = tickets.filter(area_asignada=area_asignada)
        
        # Trabajador asignado
        trabajador_asignado = form.cleaned_data.get('trabajador_asignado')
        if trabajador_asignado:
            tickets = tickets.filter(trabajador_asignado=trabajador_asignado)
        
        # Cliente
        cliente = form.cleaned_data.get('cliente')
        if cliente:
            tickets = tickets.filter(
                Q(cliente_solicitante__nombre__icontains=cliente) |
                Q(cliente_solicitante__correo_electronico__icontains=cliente)
            )
        
        # Ordenamiento
        orden = form.cleaned_data.get('orden', '-fecha_creacion')
        tickets = tickets.order_by(orden)
    else:
        # Orden por defecto
        tickets = tickets.order_by('-fecha_creacion')
    
    # Estadísticas de los tickets filtrados
    stats = tickets.aggregate(
        total=Count('id'),
        criticos=Count('id', filter=Q(nivel_critico=Ticket.NivelCritico.CRITICO)),
        en_proceso=Count('id', filter=Q(estado=Ticket.Estado.EN_PROCESO)),
        resueltos=Count('id', filter=Q(estado=Ticket.Estado.RESUELTO))
    )
    
    # Paginación
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Verificar si hay filtros activos
    filtros_activos = any([
        form.cleaned_data.get(field) for field in form.cleaned_data 
        if field != 'orden' and form.cleaned_data.get(field)
    ]) if form.is_valid() else False
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
        'filtros_activos': filtros_activos,
    }
    
    return render(request, 'core/lista_tickets.html', context)

@login_required
def ver_ticket_view(request, pk):
    """Vista detallada de un ticket con funcionalidad de observaciones"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos básicos
    puede_editar = (
        request.user == ticket.trabajador_creador or
        request.user == ticket.trabajador_asignado or
        request.user.is_superuser or
        (hasattr(request.user, 'perfil') and request.user.perfil.area == ticket.area_asignada)
    )
    
    # Manejo de observaciones (POST)
    if request.method == 'POST' and 'observacion_texto' in request.POST:
        if puede_editar:
            observacion_form = ObservacionForm(request.POST)
            if observacion_form.is_valid():
                observacion = observacion_form.save(commit=False)
                observacion.ticket_asociado = ticket
                observacion.autor_trabajador = request.user
                observacion.save()
                messages.success(request, 'Observación agregada exitosamente')
                return redirect('ver_ticket', pk=ticket.id)
    
    # Obtener todas las áreas para los modales
    areas = Area.objects.all()
    
    context = {
        'ticket': ticket,
        'puede_editar': puede_editar,
        'observacion_form': ObservacionForm(),
        'areas': areas,  # Para el modal de derivación
    }
    
    return render(request, 'core/ver_ticket.html', context)

# SPRINT 2 - NUEVAS FUNCIONALIDADES

@login_required
@require_POST
def derivar_ticket_view(request, pk):
    """Vista para derivar un ticket a otra área (HU02)"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not _puede_derivar_ticket(request.user, ticket):
        messages.error(request, 'No tienes permisos para derivar este ticket')
        return redirect('ver_ticket', pk=ticket.id)
    
    if request.method == 'POST':
        form = DerivacionForm(request.POST, ticket=ticket)
        if form.is_valid():
            # Crear derivación
            derivacion = form.save(commit=False)
            derivacion.ticket = ticket
            derivacion.area_origen = ticket.area_asignada
            derivacion.trabajador_origen = request.user
            derivacion.save()
            
            # Actualizar área del ticket
            ticket.area_asignada = derivacion.area_destino
            ticket.trabajador_asignado = None  # Desasignar al cambiar de área
            ticket.save()
            
            # Notificación (básica por ahora)
            messages.success(
                request, 
                f'Ticket derivado exitosamente a {derivacion.area_destino.nombre}'
            )
            
            # Si es AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Ticket derivado a {derivacion.area_destino.nombre}'
                })
            
            return redirect('ver_ticket', pk=ticket.id)
    
    # Si no es válido y es AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'errors': form.errors if 'form' in locals() else {}
        })
    
    return redirect('ver_ticket', pk=ticket.id)

@login_required
@require_POST
def cambiar_estado_ticket_view(request, pk):
    """Vista para cambiar el estado de un ticket (HU03)"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not _puede_cambiar_estado(request.user, ticket):
        messages.error(request, 'No tienes permisos para cambiar el estado de este ticket')
        return redirect('ver_ticket', pk=ticket.id)
    
    if request.method == 'POST':
        form = CambioEstadoForm(request.POST, ticket=ticket)
        if form.is_valid():
            nuevo_estado = form.cleaned_data['nuevo_estado']
            observacion_texto = form.cleaned_data.get('observacion')
            
            # Actualizar estado del ticket
            estado_anterior = ticket.estado
            ticket.estado = nuevo_estado
            
            # Registrar fechas según el estado
            if nuevo_estado == Ticket.Estado.RESUELTO:
                ticket.fecha_resolucion = timezone.now()
            elif nuevo_estado == Ticket.Estado.CERRADO:
                ticket.fecha_cierre = timezone.now()
            
            ticket.save()
            
            # Crear observación obligatoria para estados finales
            if observacion_texto:
                Observacion.objects.create(
                    ticket_asociado=ticket,
                    observacion_texto=f"Estado cambiado de {estado_anterior} a {nuevo_estado}. {observacion_texto}",
                    autor_trabajador=request.user
                )
            
            messages.success(request, f'Estado del ticket actualizado a {ticket.get_estado_display()}')
            
            # Si es AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'nuevo_estado': ticket.estado,
                    'nuevo_estado_display': ticket.get_estado_display()
                })
            
            return redirect('ver_ticket', pk=ticket.id)
    
    # Si es AJAX y hay error
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'errors': form.errors if 'form' in locals() else {}
        })
    
    return redirect('ver_ticket', pk=ticket.id)

@login_required
@require_POST
def agregar_observacion_view(request, pk):
    """Vista para agregar observaciones a un ticket (HU04)"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    puede_editar = (
        request.user == ticket.trabajador_creador or
        request.user == ticket.trabajador_asignado or
        request.user.is_superuser or
        (hasattr(request.user, 'perfil') and request.user.perfil.area == ticket.area_asignada)
    )
    
    if not puede_editar:
        messages.error(request, 'No tienes permisos para agregar observaciones')
        return redirect('ver_ticket', pk=ticket.id)
    
    form = ObservacionForm(request.POST)
    if form.is_valid():
        observacion = form.save(commit=False)
        observacion.ticket_asociado = ticket
        observacion.autor_trabajador = request.user
        observacion.save()
        
        messages.success(request, 'Observación agregada exitosamente')
        
        # Si es AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'observacion': {
                    'autor': observacion.autor_trabajador.get_full_name() or observacion.autor_trabajador.username,
                    'fecha': observacion.fecha_hora_observacion.strftime('%d/%m/%Y %H:%M'),
                    'texto': observacion.observacion_texto
                }
            })
    else:
        # Si es AJAX y hay error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        messages.error(request, 'Error al agregar la observación')
    
    return redirect('ver_ticket', pk=ticket.id)

# SPRINT 3 - GESTIÓN DE USUARIOS (HU07)

@login_required
def lista_usuarios_view(request):
    """Vista para listar usuarios del sistema"""
    # Verificar permisos - solo jefes y superusuarios
    if not _es_jefe_o_admin(request.user):
        messages.error(request, 'No tienes permisos para gestionar usuarios')
        return redirect('dashboard')
    
    # Obtener usuarios con información relacionada
    usuarios = User.objects.select_related('perfil__area').prefetch_related(
        'roles_jefatura'
    ).order_by('username')
    
    # Filtrar por área si el usuario es jefe (solo ve usuarios de su área)
    if not request.user.is_superuser:
        jefatura = request.user.roles_jefatura.filter(
            fecha_fin_jefatura__isnull=True
        ).first()
        if jefatura:
            usuarios = usuarios.filter(perfil__area=jefatura.area_jefatura)
    
    # Búsqueda
    busqueda = request.GET.get('busqueda')
    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )
    
    # Filtro por estado
    estado = request.GET.get('estado')
    if estado == 'activos':
        usuarios = usuarios.filter(is_active=True)
    elif estado == 'inactivos':
        usuarios = usuarios.filter(is_active=False)
    
    # Paginación
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'busqueda': busqueda,
        'estado': estado,
    }
    
    return render(request, 'core/usuarios/lista_usuarios.html', context)

@login_required
def crear_usuario_view(request):
    """Vista para crear nuevos usuarios"""
    # Verificar permisos
    if not _es_jefe_o_admin(request.user):
        messages.error(request, 'No tienes permisos para crear usuarios')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UsuarioCreacionForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request, 
                f'Usuario {usuario.username} creado exitosamente. '
                f'Se han enviado las credenciales a {usuario.email}'
            )
            
            # TODO: Enviar email con credenciales (opcional para MVP)
            
            return redirect('lista_usuarios')
    else:
        form = UsuarioCreacionForm()
        
        # Si es jefe, limitar áreas disponibles a la suya
        if not request.user.is_superuser:
            jefatura = request.user.roles_jefatura.filter(
                fecha_fin_jefatura__isnull=True
            ).first()
            if jefatura:
                form.fields['area'].queryset = Area.objects.filter(
                    id=jefatura.area_jefatura.id
                )
    
    return render(request, 'core/usuarios/crear_usuario.html', {'form': form})

@login_required
def editar_usuario_view(request, pk):
    """Vista para editar usuarios existentes"""
    usuario = get_object_or_404(User, pk=pk)
    
    # Verificar permisos
    if not _puede_editar_usuario(request.user, usuario):
        messages.error(request, 'No tienes permisos para editar este usuario')
        return redirect('lista_usuarios')
    
    if request.method == 'POST':
        form = UsuarioEdicionForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario {usuario.username} actualizado exitosamente')
            return redirect('lista_usuarios')
    else:
        form = UsuarioEdicionForm(instance=usuario)
        
        # Si es jefe, limitar áreas disponibles
        if not request.user.is_superuser:
            jefatura = request.user.roles_jefatura.filter(
                fecha_fin_jefatura__isnull=True
            ).first()
            if jefatura:
                form.fields['area'].queryset = Area.objects.filter(
                    id=jefatura.area_jefatura.id
                )
    
    context = {
        'form': form,
        'usuario': usuario
    }
    
    return render(request, 'core/usuarios/editar_usuario.html', context)

@login_required
@require_POST
def toggle_usuario_estado_view(request, pk):
    """Vista para activar/desactivar usuarios (AJAX)"""
    usuario = get_object_or_404(User, pk=pk)
    
    # Verificar permisos
    if not _puede_editar_usuario(request.user, usuario):
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos para modificar este usuario'
        }, status=403)
    
    # No permitir desactivar superusuarios
    if usuario.is_superuser and not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'No puedes desactivar a un superusuario'
        }, status=403)
    
    # Toggle estado
    usuario.is_active = not usuario.is_active
    usuario.save()
    
    return JsonResponse({
        'success': True,
        'is_active': usuario.is_active,
        'message': f'Usuario {"activado" if usuario.is_active else "desactivado"} exitosamente'
    })

# Funciones auxiliares de permisos

def _puede_derivar_ticket(user, ticket):
    """Verifica si un usuario puede derivar un ticket"""
    # Solo tickets abiertos se pueden derivar
    if ticket.estado != Ticket.Estado.ABIERTO:
        return False
    
    # Superusuarios siempre pueden
    if user.is_superuser:
        return True
    
    # Usuario del área asignada
    if hasattr(user, 'perfil') and user.perfil.area == ticket.area_asignada:
        return True
    
    # Jefe del área asignada
    if user.roles_jefatura.filter(
        area_jefatura=ticket.area_asignada,
        fecha_fin_jefatura__isnull=True
    ).exists():
        return True
    
    return False

def _puede_cambiar_estado(user, ticket):
    """Verifica si un usuario puede cambiar el estado de un ticket"""
    # Superusuarios siempre pueden
    if user.is_superuser:
        return True
    
    # Usuario asignado al ticket
    if user == ticket.trabajador_asignado:
        return True
    
    # Usuario del área asignada
    if hasattr(user, 'perfil') and user.perfil.area == ticket.area_asignada:
        return True
    
    # Jefe del área asignada
    if user.roles_jefatura.filter(
        area_jefatura=ticket.area_asignada,
        fecha_fin_jefatura__isnull=True
    ).exists():
        return True
    
    return False

def _es_jefe_o_admin(user):
    """Verifica si el usuario es jefe de área o administrador"""
    if user.is_superuser:
        return True
    
    return user.roles_jefatura.filter(
        fecha_fin_jefatura__isnull=True
    ).exists()

def _puede_editar_usuario(user, usuario_a_editar):
    """Verifica si un usuario puede editar a otro"""
    # Superusuarios pueden editar a cualquiera
    if user.is_superuser:
        return True
    
    # No se puede editar a sí mismo (excepto superusuarios)
    if user == usuario_a_editar:
        return False
    
    # Jefes pueden editar usuarios de su área
    jefatura = user.roles_jefatura.filter(
        fecha_fin_jefatura__isnull=True
    ).first()
    
    if jefatura and hasattr(usuario_a_editar, 'perfil'):
        return usuario_a_editar.perfil.area == jefatura.area_jefatura
    
    return False