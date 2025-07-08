from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Area, Cliente, Ticket, Observacion
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Crea tickets de prueba para el Sprint 2'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creando tickets de prueba para Sprint 2...')

        # Obtener datos existentes
        areas = list(Area.objects.all())
        clientes = list(Cliente.objects.all())
        usuarios = list(User.objects.filter(is_superuser=False))
        
        if not areas or not clientes or not usuarios:
            self.stdout.write(self.style.ERROR('Asegúrate de ejecutar crear_datos_iniciales primero'))
            return

        # Tipos de problemas comunes
        tipos_problema = [
            'Hardware', 'Software', 'Red', 'Acceso', 'Email', 
            'Impresora', 'Sistema', 'Base de datos', 'Servidor', 'Otro'
        ]

        # Crear tickets de prueba
        tickets_data = [
            {
                'titulo': 'PC no enciende en oficina 201',
                'descripcion': 'El computador de la oficina 201 no enciende. Se revisó el cable de poder y está bien conectado.',
                'nivel': Ticket.NivelCritico.ALTO,
                'tipo': 'Hardware',
                'estado': Ticket.Estado.ABIERTO
            },
            {
                'titulo': 'Error al iniciar sesión en sistema ERP',
                'descripcion': 'Usuario reporta error "Credenciales inválidas" al intentar ingresar al sistema ERP. Ya se verificó que el usuario y contraseña son correctos.',
                'nivel': Ticket.NivelCritico.MEDIO,
                'tipo': 'Sistema',
                'estado': Ticket.Estado.ABIERTO
            },
            {
                'titulo': 'Solicitud de acceso a carpeta compartida',
                'descripcion': 'Necesito acceso a la carpeta "Finanzas 2025" en el servidor. Es urgente para el cierre mensual.',
                'nivel': Ticket.NivelCritico.CRITICO,
                'tipo': 'Acceso',
                'estado': Ticket.Estado.EN_PROCESO
            },
            {
                'titulo': 'Impresora del segundo piso atascada',
                'descripcion': 'La impresora HP del segundo piso tiene papel atascado. Se intentó remover pero no se puede acceder.',
                'nivel': Ticket.NivelCritico.BAJO,
                'tipo': 'Impresora',
                'estado': Ticket.Estado.ABIERTO
            },
            {
                'titulo': 'Lentitud en conexión a internet',
                'descripcion': 'Varios usuarios del área de ventas reportan lentitud extrema en la navegación web desde esta mañana.',
                'nivel': Ticket.NivelCritico.ALTO,
                'tipo': 'Red',
                'estado': Ticket.Estado.EN_PROCESO
            },
            {
                'titulo': 'No puedo enviar correos con archivos adjuntos',
                'descripcion': 'Al intentar enviar correos con archivos adjuntos mayores a 5MB, el sistema muestra error de timeout.',
                'nivel': Ticket.NivelCritico.MEDIO,
                'tipo': 'Email',
                'estado': Ticket.Estado.ABIERTO
            },
        ]

        tickets_creados = []
        
        for data in tickets_data:
            # Seleccionar datos aleatorios
            area = random.choice(areas)
            cliente = random.choice(clientes)
            creador = random.choice(usuarios)
            
            # Crear ticket
            ticket = Ticket.objects.create(
                titulo=data['titulo'],
                estado=data['estado'],
                descripcion_problema=data['descripcion'],
                nivel_critico=data['nivel'],
                tipo_problema=data['tipo'],
                cliente_solicitante=cliente,
                area_asignada=area,
                trabajador_creador=creador,
                trabajador_asignado=random.choice(usuarios) if data['estado'] != Ticket.Estado.ABIERTO else None
            )
            
            # Ajustar fecha de creación para que parezca más realista
            dias_atras = random.randint(0, 7)
            ticket.fecha_creacion = timezone.now() - timedelta(days=dias_atras)
            ticket.save()
            
            tickets_creados.append(ticket)
            self.stdout.write(f'✓ Ticket #{ticket.id}: {ticket.titulo}')

        # Agregar algunas observaciones de prueba
        observaciones_texto = [
            "Se contactó al usuario para obtener más información.",
            "Problema identificado, trabajando en la solución.",
            "Se requiere autorización del jefe de área para proceder.",
            "Usuario confirmó que el problema persiste.",
            "Se escaló al equipo de infraestructura.",
            "Solución temporal implementada, monitoreando.",
        ]

        for ticket in random.sample(tickets_creados, min(3, len(tickets_creados))):
            for i in range(random.randint(1, 3)):
                Observacion.objects.create(
                    ticket_asociado=ticket,
                    observacion_texto=random.choice(observaciones_texto),
                    autor_trabajador=random.choice(usuarios)
                )
            self.stdout.write(f'  ✓ Agregadas observaciones al ticket #{ticket.id}')

        self.stdout.write(self.style.SUCCESS(f'\n¡{len(tickets_creados)} tickets de prueba creados exitosamente!'))
        self.stdout.write('\nPuedes usar estos tickets para probar:')
        self.stdout.write('- Derivación entre áreas (tickets ABIERTOS)')
        self.stdout.write('- Cambio de estado (todos los tickets)')
        self.stdout.write('- Sistema de observaciones')
        self.stdout.write('- Historial de derivaciones')