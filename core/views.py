from django import forms
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
    UsuarioCreacionForm, UsuarioEdicionForm, GrupoForm, DesactivacionUsuarioForm
)
from .models import Ticket, Cliente, Area, Perfil, Jefatura, Derivacion, Observacion, Grupo, HistorialUsuario

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
    tickets_sin_asignar = []
    tickets_sin_asignar_total = 0
    stats_asignacion = {}
    carga_trabajo = []
    
    if hasattr(request.user, 'perfil') and request.user.perfil.area:
        area = request.user.perfil.area
        
        # Tickets del área
        tickets_area = Ticket.objects.filter(
            area_asignada=area
        ).order_by('-fecha_creacion')[:5]
        
        # Tickets sin asignar del área
        tickets_sin_asignar = Ticket.objects.filter(
            area_asignada=area,
            trabajador_asignado__isnull=True,
            estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
        ).order_by('-nivel_critico', '-fecha_creacion')[:5]
        
        tickets_sin_asignar_total = Ticket.objects.filter(
            area_asignada=area,
            trabajador_asignado__isnull=True,
            estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
        ).count()
        
        # Estadísticas de asignación (solo para jefes)
        if request.user.roles_jefatura.filter(fecha_fin_jefatura__isnull=True).exists():
            tickets_area_total = Ticket.objects.filter(area_asignada=area)
            sin_asignar = tickets_area_total.filter(trabajador_asignado__isnull=True).count()
            asignados = tickets_area_total.filter(trabajador_asignado__isnull=False).count()
            trabajadores_activos = User.objects.filter(
                perfil__area=area, 
                is_active=True
            ).exclude(roles_jefatura__isnull=False).count()
            
            stats_asignacion = {
                'sin_asignar': sin_asignar,
                'asignados': asignados,
                'trabajadores_activos': trabajadores_activos
            }
            
            # Carga de trabajo por trabajador
            trabajadores = User.objects.filter(perfil__area=area, is_active=True)
            for trabajador in trabajadores:
                tickets_asignados = trabajador.tickets_asignados.filter(
                    estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
                ).count()
                carga_trabajo.append({
                    'nombre': trabajador.get_full_name() or trabajador.username,
                    'tickets_asignados': tickets_asignados
                })
            
            # Ordenar por carga de trabajo
            carga_trabajo.sort(key=lambda x: x['tickets_asignados'], reverse=True)
    
    context = {
        'total_tickets': total_tickets,
        'tickets_abiertos': tickets_abiertos,
        'tickets_en_proceso': tickets_en_proceso,
        'tickets_resueltos': tickets_resueltos,
        'mis_tickets': mis_tickets,
        'tickets_area': tickets_area,
        'tickets_sin_asignar': tickets_sin_asignar,
        'tickets_sin_asignar_total': tickets_sin_asignar_total,
        'stats_asignacion': stats_asignacion,
        'carga_trabajo': carga_trabajo[:5],  # Solo mostrar top 5
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
    
    # Tickets sin asignar para gestión
    tickets_sin_asignar_jefe = Ticket.objects.filter(
        area_asignada=area_jefatura,
        trabajador_asignado__isnull=True,
        estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
    ).order_by('-nivel_critico', '-fecha_creacion')
    
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
        'tickets_sin_asignar_jefe': tickets_sin_asignar_jefe,
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
    
    # Obtener todas las áreas para los modales
    areas = Area.objects.all()
    
    # Obtener trabajadores del área para asignación (solo para jefes)
    trabajadores_area = []
    if request.user.roles_jefatura.filter(
        area_jefatura=ticket.area_asignada,
        fecha_fin_jefatura__isnull=True
    ).exists():
        trabajadores_area = ticket.area_asignada.miembros.filter(usuario__is_active=True)
    
    context = {
        'ticket': ticket,
        'puede_editar': puede_editar,
        'observacion_form': ObservacionForm(),
        'areas': areas,
        'trabajadores_area': trabajadores_area,
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

# SPRINT 4 - GESTIÓN ADMINISTRATIVA AVANZADA

# Importar los nuevos modelos al principio del archivo:
# from .models import Grupo, HistorialUsuario
# from .forms import GrupoForm, DesactivacionUsuarioForm

@login_required
def lista_grupos_view(request):
    """Vista para listar grupos del sistema (HU08)"""
    # Verificar permisos - solo jefes y superusuarios
    if not _es_jefe_o_admin(request.user):
        messages.error(request, 'No tienes permisos para gestionar grupos')
        return redirect('dashboard')
    
    # Obtener grupos con información relacionada
    grupos = Grupo.objects.prefetch_related('areas').select_related('creado_por')
    
    # Filtrar solo activos por defecto
    mostrar_inactivos = request.GET.get('inactivos', False)
    if not mostrar_inactivos:
        grupos = grupos.filter(activo=True)
    
    # Búsqueda
    busqueda = request.GET.get('busqueda')
    if busqueda:
        grupos = grupos.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    
    # Estadísticas
    stats = {
        'total': grupos.count(),
        'activos': grupos.filter(activo=True).count(),
        'inactivos': grupos.filter(activo=False).count(),
        'total_areas': Area.objects.count()
    }
    
    context = {
        'grupos': grupos,
        'busqueda': busqueda,
        'mostrar_inactivos': mostrar_inactivos,
        'stats': stats
    }
    
    return render(request, 'core/grupos/lista_grupos.html', context)

@login_required
def crear_grupo_view(request):
    """Vista para crear nuevos grupos (HU08)"""
    # Verificar permisos
    if not _es_jefe_o_admin(request.user):
        messages.error(request, 'No tienes permisos para crear grupos')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = GrupoForm(request.POST)
        if form.is_valid():
            grupo = form.save(commit=False)
            grupo.creado_por = request.user
            grupo.save()
            form.save_m2m()  # Guardar relaciones many-to-many
            
            # Registrar en historial
            HistorialUsuario.objects.create(
                usuario=request.user,
                tipo_accion=HistorialUsuario.TipoAccion.CAMBIO_ROL,
                descripcion=f'Creó el grupo "{grupo.nombre}"',
                realizado_por=request.user,
                datos_adicionales={
                    'grupo_id': grupo.id,
                    'areas_count': grupo.areas.count()
                }
            )
            
            messages.success(request, f'Grupo "{grupo.nombre}" creado exitosamente')
            return redirect('lista_grupos')
    else:
        form = GrupoForm()
    
    return render(request, 'core/grupos/crear_grupo.html', {'form': form})

@login_required
def editar_grupo_view(request, pk):
    """Vista para editar grupos existentes (HU08)"""
    grupo = get_object_or_404(Grupo, pk=pk)
    
    # Verificar permisos
    if not _es_jefe_o_admin(request.user):
        messages.error(request, 'No tienes permisos para editar grupos')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = GrupoForm(request.POST, instance=grupo)
        if form.is_valid():
            # Guardar áreas anteriores para comparar
            areas_antes = set(grupo.areas.all())
            
            grupo = form.save()
            
            # Verificar cambios en áreas
            areas_despues = set(grupo.areas.all())
            if areas_antes != areas_despues:
                agregadas = areas_despues - areas_antes
                removidas = areas_antes - areas_despues
                
                cambios = []
                if agregadas:
                    cambios.append(f"Agregadas: {', '.join([a.nombre for a in agregadas])}")
                if removidas:
                    cambios.append(f"Removidas: {', '.join([a.nombre for a in removidas])}")
                
                HistorialUsuario.objects.create(
                    usuario=request.user,
                    tipo_accion=HistorialUsuario.TipoAccion.CAMBIO_ROL,
                    descripcion=f'Modificó el grupo "{grupo.nombre}". {"; ".join(cambios)}',
                    realizado_por=request.user,
                    datos_adicionales={
                        'grupo_id': grupo.id,
                        'areas_agregadas': [a.id for a in agregadas],
                        'areas_removidas': [a.id for a in removidas]
                    }
                )
            
            messages.success(request, f'Grupo "{grupo.nombre}" actualizado exitosamente')
            return redirect('lista_grupos')
    else:
        form = GrupoForm(instance=grupo)
    
    context = {
        'form': form,
        'grupo': grupo
    }
    
    return render(request, 'core/grupos/editar_grupo.html', context)

@login_required
@require_POST
def eliminar_grupo_view(request, pk):
    """Vista para eliminar (desactivar) grupos (HU08)"""
    grupo = get_object_or_404(Grupo, pk=pk)
    
    # Verificar permisos
    if not _es_jefe_o_admin(request.user):
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos para eliminar grupos'
        }, status=403)
    
    # Verificar si puede ser eliminado
    if not grupo.puede_eliminar():
        return JsonResponse({
            'success': False,
            'error': 'Este grupo no puede ser eliminado porque tiene dependencias activas'
        })
    
    # Soft delete - solo desactivar
    grupo.activo = False
    grupo.save()
    
    # Registrar en historial
    HistorialUsuario.objects.create(
        usuario=request.user,
        tipo_accion=HistorialUsuario.TipoAccion.CAMBIO_ROL,
        descripcion=f'Desactivó el grupo "{grupo.nombre}"',
        realizado_por=request.user,
        datos_adicionales={
            'grupo_id': grupo.id,
            'areas_afectadas': list(grupo.areas.values_list('nombre', flat=True))
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Grupo "{grupo.nombre}" desactivado exitosamente'
    })

@login_required
def desactivar_usuario_view(request, pk):
    """Vista mejorada para desactivar usuarios con registro de historial (HU10)"""
    usuario = get_object_or_404(User, pk=pk)
    
    # Verificar permisos
    if not _puede_editar_usuario(request.user, usuario):
        messages.error(request, 'No tienes permisos para desactivar este usuario')
        return redirect('lista_usuarios')
    
    # No permitir desactivar superusuarios
    if usuario.is_superuser and not request.user.is_superuser:
        messages.error(request, 'No puedes desactivar a un superusuario')
        return redirect('lista_usuarios')
    
    # Obtener información de impacto
    tickets_abiertos = usuario.tickets_asignados.filter(
        estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
    ).count()
    
    if request.method == 'POST':
        form = DesactivacionUsuarioForm(request.POST)
        if form.is_valid():
            motivo = form.cleaned_data['motivo']
            
            # Desactivar usuario
            usuario.is_active = False
            usuario.save()
            
            # Registrar en historial
            HistorialUsuario.objects.create(
                usuario=usuario,
                tipo_accion=HistorialUsuario.TipoAccion.DESACTIVACION,
                descripcion=motivo,
                realizado_por=request.user,
                datos_adicionales={
                    'tickets_abiertos': tickets_abiertos,
                    'area': usuario.perfil.area.nombre if hasattr(usuario, 'perfil') and usuario.perfil.area else None,
                    'era_jefe': usuario.roles_jefatura.filter(fecha_fin_jefatura__isnull=True).exists()
                }
            )
            
            # Finalizar jefaturas activas si las tiene
            usuario.roles_jefatura.filter(
                fecha_fin_jefatura__isnull=True
            ).update(fecha_fin_jefatura=timezone.now().date())
            
            messages.success(
                request, 
                f'Usuario {usuario.username} desactivado exitosamente. '
                f'Sus {tickets_abiertos} tickets abiertos deberán ser reasignados.'
            )
            
            # Si es AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Usuario desactivado exitosamente'
                })
            
            return redirect('lista_usuarios')
    else:
        form = DesactivacionUsuarioForm()
    
    context = {
        'form': form,
        'usuario': usuario,
        'tickets_abiertos': tickets_abiertos,
        'es_jefe': usuario.roles_jefatura.filter(fecha_fin_jefatura__isnull=True).exists()
    }
    
    return render(request, 'core/usuarios/desactivar_usuario.html', context)

@login_required
def historial_usuario_view(request, pk):
    """Vista para ver el historial de cambios de un usuario (HU10)"""
    usuario = get_object_or_404(User, pk=pk)
    
    # Verificar permisos - solo el mismo usuario, jefes o admins
    if not (request.user == usuario or _es_jefe_o_admin(request.user)):
        messages.error(request, 'No tienes permisos para ver este historial')
        return redirect('dashboard')
    
    historial = usuario.historial_cambios.select_related('realizado_por').order_by('-fecha_accion')
    
    context = {
        'usuario': usuario,
        'historial': historial
    }
    
    return render(request, 'core/usuarios/historial_usuario.html', context)

# Modificar la función auxiliar de TicketForm para excluir usuarios inactivos
def get_usuarios_activos_choices():
    """Obtiene solo usuarios activos para asignación de tickets"""
    return User.objects.filter(
        is_active=True
    ).select_related('perfil__area').order_by('first_name', 'last_name')

@login_required
@require_POST
def asignar_ticket_view(request, pk):
    """Vista para asignar un ticket a un trabajador"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not _puede_asignar_ticket(request.user, ticket):
        messages.error(request, 'No tienes permisos para asignar este ticket')
        return redirect('ver_ticket', pk=ticket.id)
    
    trabajador_id = request.POST.get('trabajador_asignado')
    
    if trabajador_id:
        try:
            trabajador = User.objects.get(id=trabajador_id)
            
            # Verificar que el trabajador pertenezca al área del ticket
            if hasattr(trabajador, 'perfil') and trabajador.perfil.area == ticket.area_asignada:
                ticket.trabajador_asignado = trabajador
                ticket.save()
                
                # Crear observación automática
                Observacion.objects.create(
                    ticket_asociado=ticket,
                    observacion_texto=f"Ticket asignado a {trabajador.get_full_name() or trabajador.username}",
                    autor_trabajador=request.user
                )
                
                messages.success(request, f'Ticket asignado a {trabajador.get_full_name() or trabajador.username}')
            else:
                messages.error(request, 'El trabajador debe pertenecer al área del ticket')
                
        except User.DoesNotExist:
            messages.error(request, 'Trabajador no encontrado')
    else:
        # Desasignar ticket
        trabajador_anterior = ticket.trabajador_asignado
        ticket.trabajador_asignado = None
        ticket.save()
        
        if trabajador_anterior:
            Observacion.objects.create(
                ticket_asociado=ticket,
                observacion_texto=f"Ticket desasignado de {trabajador_anterior.get_full_name() or trabajador_anterior.username}",
                autor_trabajador=request.user
            )
        
        messages.success(request, 'Ticket desasignado exitosamente')
    
    # Si es AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        trabajador = ticket.trabajador_asignado
        return JsonResponse({
            'success': True,
            'trabajador_nombre': trabajador.get_full_name() or trabajador.username if trabajador else None,
            'trabajador_id': trabajador.id if trabajador else None
        })
    
    return redirect('ver_ticket', pk=ticket.id)

@login_required
@require_POST
def tomar_ticket_view(request, pk):
    """Vista para que un trabajador tome un ticket sin asignar de su área"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar que el ticket no esté asignado
    if ticket.trabajador_asignado:
        messages.error(request, 'Este ticket ya está asignado')
        return redirect('ver_ticket', pk=ticket.id)
    
    # Verificar que el usuario pertenezca al área del ticket
    if not (hasattr(request.user, 'perfil') and request.user.perfil.area == ticket.area_asignada):
        messages.error(request, 'Solo puedes tomar tickets de tu área')
        return redirect('ver_ticket', pk=ticket.id)
    
    # Asignar ticket al usuario actual
    ticket.trabajador_asignado = request.user
    ticket.save()
    
    # Crear observación
    Observacion.objects.create(
        ticket_asociado=ticket,
        observacion_texto=f"Ticket tomado por {request.user.get_full_name() or request.user.username}",
        autor_trabajador=request.user
    )
    
    messages.success(request, 'Has tomado este ticket exitosamente')
    
    # Si es AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'trabajador_nombre': request.user.get_full_name() or request.user.username,
            'trabajador_id': request.user.id
        })
    
    return redirect('ver_ticket', pk=ticket.id)

@login_required
def tickets_sin_asignar_view(request):
    """Vista para mostrar tickets sin asignar del área del usuario"""
    if not hasattr(request.user, 'perfil') or not request.user.perfil.area:
        messages.error(request, 'Debes estar asignado a un área para ver tickets sin asignar')
        return redirect('dashboard')
    
    tickets = Ticket.objects.filter(
        area_asignada=request.user.perfil.area,
        trabajador_asignado__isnull=True,
        estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
    ).order_by('-nivel_critico', '-fecha_creacion')
    
    # Paginación
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'area': request.user.perfil.area
    }
    
    return render(request, 'core/tickets_sin_asignar.html', context)

# 2. FUNCIONES AUXILIARES DE PERMISOS

def _puede_asignar_ticket(user, ticket):
    """Verifica si un usuario puede asignar un ticket"""
    # Superusuarios siempre pueden
    if user.is_superuser:
        return True
    
    # Jefe del área del ticket
    if user.roles_jefatura.filter(
        area_jefatura=ticket.area_asignada,
        fecha_fin_jefatura__isnull=True
    ).exists():
        return True
    
    return False
