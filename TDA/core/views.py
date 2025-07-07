from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import CustomLoginForm, TicketForm, ClienteForm
from .models import Ticket, Cliente, Area, Perfil, Jefatura
from django.utils import timezone

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
    """Vista de lista de tickets con filtros y paginación"""
    # Obtener todos los tickets
    tickets = Ticket.objects.all()
    
    # Filtrar por estado si se proporciona
    estado = request.GET.get('estado')
    if estado:
        tickets = tickets.filter(estado=estado)
    
    # Filtrar por nivel crítico
    nivel = request.GET.get('nivel')
    if nivel:
        tickets = tickets.filter(nivel_critico=nivel)
    
    # Filtrar por área
    area_id = request.GET.get('area')
    if area_id:
        tickets = tickets.filter(area_asignada_id=area_id)
    
    # Búsqueda por título o ID
    busqueda = request.GET.get('busqueda')
    if busqueda:
        tickets = tickets.filter(
            Q(titulo__icontains=busqueda) |
            Q(id__icontains=busqueda)
        )
    
    # Ordenamiento
    orden = request.GET.get('orden', '-fecha_creacion')
    tickets = tickets.order_by(orden)
    
    # Paginación
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener áreas para el filtro
    areas = Area.objects.all()
    
    context = {
        'page_obj': page_obj,
        'areas': areas,
        'estados': Ticket.Estado.choices,
        'niveles': Ticket.NivelCritico.choices,
        'filtros_activos': {
            'estado': estado,
            'nivel': nivel,
            'area': area_id,
            'busqueda': busqueda,
            'orden': orden,
        }
    }
    
    return render(request, 'core/lista_tickets.html', context)

@login_required
def ver_ticket_view(request, pk):
    """Vista detallada de un ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos básicos (puede ser expandido)
    puede_editar = (
        request.user == ticket.trabajador_creador or
        request.user == ticket.trabajador_asignado or
        request.user.is_superuser
    )
    
    context = {
        'ticket': ticket,
        'puede_editar': puede_editar,
    }
    
    return render(request, 'core/ver_ticket.html', context)