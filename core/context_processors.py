def tickets_sin_asignar_count(request):
    """Context processor para mostrar contador de tickets sin asignar en navegación"""
    if request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.area:
        count = Ticket.objects.filter(
            area_asignada=request.user.perfil.area,
            trabajador_asignado__isnull=True,
            estado__in=[Ticket.Estado.ABIERTO, Ticket.Estado.EN_PROCESO]
        ).count()
        return {'tickets_sin_asignar_count': count}
    return {'tickets_sin_asignar_count': 0}