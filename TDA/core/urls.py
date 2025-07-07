from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.home_view, name='home'),
    
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
]