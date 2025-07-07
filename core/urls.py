from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.home_view, name='home'),
    
    #Sprint 1 - Autenticación y dashboards
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboards
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/jefatura/', views.dashboard_jefatura_view, name='dashboard_jefatura'),
    
    # Tickets
    path('tickets/', views.lista_tickets_view, name='lista_tickets'),
    path('tickets/crear/', views.crear_ticket_view, name='crear_ticket'),
    path('tickets/<int:pk>/', views.ver_ticket_view, name='ver_ticket'),

    # SPRINT 2 - Nuevas funcionalidades
    # HU02 - Derivación de tickets
    path('tickets/<int:pk>/derivar/', views.derivar_ticket_view, name='derivar_ticket'),
    
    # HU03 - Cambio de estado
    path('tickets/<int:pk>/cambiar-estado/', views.cambiar_estado_ticket_view, name='cambiar_estado_ticket'),
    
    # HU04 - Observaciones
    path('tickets/<int:pk>/observacion/', views.agregar_observacion_view, name='agregar_observacion'),
    
    # SPRINT 3 - Gestión de usuarios (HU07)
    path('usuarios/', views.lista_usuarios_view, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario_view, name='crear_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario_view, name='editar_usuario_view'),
    path('usuarios/<int:pk>/toggle-estado/', views.toggle_usuario_estado_view, name='toggle_usuario_estado'),
]