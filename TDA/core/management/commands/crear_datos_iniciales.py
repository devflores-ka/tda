from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Area, Departamento, Perfil, Jefatura, Cliente
from django.utils import timezone
from datetime import datetime

class Command(BaseCommand):
    help = 'Crea datos iniciales para el sistema de tickets'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creando datos iniciales...')

        # Crear áreas
        area_ti = Area.objects.get_or_create(nombre='Tecnología de la Información')[0]
        area_rrhh = Area.objects.get_or_create(nombre='Recursos Humanos')[0]
        area_finanzas = Area.objects.get_or_create(nombre='Finanzas')[0]
        area_operaciones = Area.objects.get_or_create(nombre='Operaciones')[0]
        
        self.stdout.write(self.style.SUCCESS('✓ Áreas creadas'))

        # Crear departamentos
        Departamento.objects.get_or_create(nombre='Soporte Técnico', area=area_ti)
        Departamento.objects.get_or_create(nombre='Desarrollo', area=area_ti)
        Departamento.objects.get_or_create(nombre='Infraestructura', area=area_ti)
        
        Departamento.objects.get_or_create(nombre='Gestión de Personal', area=area_rrhh)
        Departamento.objects.get_or_create(nombre='Capacitación', area=area_rrhh)
        
        Departamento.objects.get_or_create(nombre='Contabilidad', area=area_finanzas)
        Departamento.objects.get_or_create(nombre='Tesorería', area=area_finanzas)
        
        self.stdout.write(self.style.SUCCESS('✓ Departamentos creados'))

        # Crear usuarios de prueba
        usuarios_data = [
            {
                'username': 'admin',
                'password': 'admin123',
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'email': 'admin@sistema.com',
                'is_superuser': True,
                'is_staff': True,
                'area': None
            },
            {
                'username': 'jefe_ti',
                'password': 'jefe123',
                'first_name': 'Carlos',
                'last_name': 'Martínez',
                'email': 'carlos.martinez@empresa.com',
                'is_superuser': False,
                'is_staff': True,
                'area': area_ti,
                'es_jefe': True
            },
            {
                'username': 'soporte1',
                'password': 'soporte123',
                'first_name': 'Ana',
                'last_name': 'García',
                'email': 'ana.garcia@empresa.com',
                'is_superuser': False,
                'is_staff': False,
                'area': area_ti
            },
            {
                'username': 'soporte2',
                'password': 'soporte123',
                'first_name': 'Pedro',
                'last_name': 'López',
                'email': 'pedro.lopez@empresa.com',
                'is_superuser': False,
                'is_staff': False,
                'area': area_ti
            },
            {
                'username': 'rrhh1',
                'password': 'rrhh123',
                'first_name': 'María',
                'last_name': 'Rodríguez',
                'email': 'maria.rodriguez@empresa.com',
                'is_superuser': False,
                'is_staff': False,
                'area': area_rrhh
            }
        ]

        for user_data in usuarios_data:
            username = user_data['username']
            es_jefe = user_data.get('es_jefe', False)
            area = user_data.get('area')
            
            # Crear o actualizar usuario
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'email': user_data['email'],
                    'is_superuser': user_data['is_superuser'],
                    'is_staff': user_data['is_staff']
                }
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'✓ Usuario {username} creado')
            else:
                self.stdout.write(f'- Usuario {username} ya existe')
            
            # Crear perfil si tiene área
            if area:
                perfil, _ = Perfil.objects.get_or_create(
                    usuario=user,
                    defaults={'area': area}
                )
                
                # Si es jefe, crear jefatura
                if es_jefe:
                    Jefatura.objects.get_or_create(
                        trabajador_jefe=user,
                        area_jefatura=area,
                        defaults={
                            'fecha_inicio_jefatura': timezone.now().date()
                        }
                    )
                    self.stdout.write(f'  ✓ Jefatura asignada a {username} en {area.nombre}')

        # Crear algunos clientes de prueba
        clientes_data = [
            {
                'nombre': 'Juan Pérez',
                'telefono': '+56912345678',
                'correo_electronico': 'juan.perez@gmail.com'
            },
            {
                'nombre': 'María Silva',
                'telefono': '+56987654321',
                'correo_electronico': 'maria.silva@hotmail.com'
            },
            {
                'nombre': 'Empresa ABC Ltda.',
                'telefono': '+56223456789',
                'correo_electronico': 'contacto@empresaabc.cl'
            },
            {
                'nombre': 'Roberto González',
                'correo_electronico': 'roberto.gonzalez@yahoo.com'
            }
        ]

        for cliente_data in clientes_data:
            cliente, created = Cliente.objects.get_or_create(
                correo_electronico=cliente_data['correo_electronico'],
                defaults={
                    'nombre': cliente_data['nombre'],
                    'telefono': cliente_data.get('telefono', '')
                }
            )
            if created:
                self.stdout.write(f'✓ Cliente {cliente.nombre} creado')

        self.stdout.write(self.style.SUCCESS('\n¡Datos iniciales creados exitosamente!'))
        self.stdout.write('\nUsuarios creados:')
        self.stdout.write('  - admin / admin123 (Superusuario)')
        self.stdout.write('  - jefe_ti / jefe123 (Jefe de TI)')
        self.stdout.write('  - soporte1 / soporte123 (Soporte TI)')
        self.stdout.write('  - soporte2 / soporte123 (Soporte TI)')
        self.stdout.write('  - rrhh1 / rrhh123 (RRHH)')
        self.stdout.write('\nPuedes usar estos usuarios para probar el sistema.')