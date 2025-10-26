from app1.models import Rifa, RifaImage
from app1.models import Compra
from app1 import crud as app1_crud


def crear_rifa(titulo, fecha_sorteo, total_tickets=100, descripcion='', fotos=None, precio=0.0):
    rifa = Rifa(titulo=titulo, fecha_sorteo=fecha_sorteo, total_tickets=total_tickets, descripcion=descripcion, precio=precio)
    rifa.save()

    # Guardar hasta 3 imágenes (fotos puede ser lista de archivos por slot)
    if fotos:
        count = 0
        for f in fotos:
            if not f:
                continue
            if count >= 3:
                break
            RifaImage.objects.create(rifa=rifa, image=f)  # image debe tener upload_to='rifas/'
            count += 1

    return rifa


def obtener_rifas():
    return Rifa.objects.all().prefetch_related('images')


def eliminar_rifa(rifa_id):
    Rifa.objects.filter(id=rifa_id).delete()


def actualizar_rifa(rifa_id, titulo=None, fecha_sorteo=None, total_tickets=None, descripcion=None, foto=None, precio=None):
    rifa = Rifa.objects.get(id=rifa_id)
    if titulo is not None:
        rifa.titulo = titulo
    if fecha_sorteo is not None:
        rifa.fecha_sorteo = fecha_sorteo
    if total_tickets is not None:
        rifa.total_tickets = total_tickets
    if descripcion is not None:
        rifa.descripcion = descripcion
    if precio is not None:
        rifa.precio = precio
    if foto is not None:
        rifa.foto = foto
    rifa.save()
    return rifa


def editar_rifa(rifa_id, titulo=None, fecha_sorteo=None, total_tickets=None, descripcion=None, precio=None, fotos_edit_slots=None):
    """Helper used by admin views to edit basic rifa params."""
    rifa = Rifa.objects.get(id=rifa_id)
    if titulo is not None:
        rifa.titulo = titulo
    if fecha_sorteo is not None:
        rifa.fecha_sorteo = fecha_sorteo
    if total_tickets is not None:
        rifa.total_tickets = total_tickets
    if descripcion is not None:
        rifa.descripcion = descripcion
    if precio is not None:
        rifa.precio = precio
    rifa.save()

    # fotos_edit_slots: lista con hasta 3 elementos que pueden ser archivo o None
    if fotos_edit_slots:
        # obtener imágenes actuales ordenadas (si existen)
        existing = list(rifa.images.all())
        # for each slot, if provided replace the image in that slot (or create new)
        for idx, f in enumerate(fotos_edit_slots):
            if not f:
                continue
            try:
                if idx < len(existing):
                    img_obj = existing[idx]
                    # reemplazar archivo
                    img_obj.image = f
                    img_obj.save()
                else:
                    # crear nueva imagen si el slot no existía
                    RifaImage.objects.create(rifa=rifa, image=f)
            except Exception:
                # ignore individual failures to keep update robust
                continue
    return rifa


def obtener_compras_pendientes(rifa_id=None):
    qs = Compra.objects.filter(estado='PENDIENTE').select_related('rifa', 'participante')
    if rifa_id:
        try:
            qs = qs.filter(rifa_id=int(rifa_id))
        except (ValueError, TypeError):
            pass
    return qs


def obtener_historial_compras(rifa_id=None):
    """Devuelve todas las compras (cualquier estado). Opcionalmente filtra por rifa_id."""
    qs = Compra.objects.all().select_related('rifa', 'participante').order_by('-creado_en')
    if rifa_id:
        try:
            qs = qs.filter(rifa_id=int(rifa_id))
        except (ValueError, TypeError):
            pass
    return qs


def get_compra(compra_id):
    return Compra.objects.select_related('rifa', 'participante').get(id=compra_id)


def confirmar_compra(compra_id):
    compra = get_compra(compra_id)
    # delegar la asignación de tickets al crud de app1
    assigned = app1_crud.asignar_tickets_a_compra(compra)
    return compra, assigned


def rechazar_compra(compra_id):
    compra = get_compra(compra_id)
    # eliminar tickets reservados asociados a la compra
    from app1.models import Ticket
    Ticket.objects.filter(compra=compra).delete()
    compra.estado = 'RECHAZADO'
    compra.save()
    return compra


def perform_sorteo(rifa_id, force=False):
    """Elige aleatoriamente un ticket confirmado para la rifa y lo guarda como ganador.

    Devuelve el objeto Ticket seleccionado o None si no se pudo seleccionar.
    """
    from app1.models import Ticket
    try:
        rifa = Rifa.objects.get(id=rifa_id)
    except Rifa.DoesNotExist:
        return None

    # Si ya tiene ganador y no se fuerza, no permitir otro sorteo
    if getattr(rifa, 'winner_ticket', None) and not force:
        return None

    # tickets confirmados
    tickets = list(Ticket.objects.filter(rifa=rifa, confirmed=True))
    if not tickets:
        return None

    import random
    winner = random.choice(tickets)
    rifa.winner_ticket = winner
    rifa.save()
    return winner

def asignar_ganador_manual(rifa_id, ticket_number):
    """Asignar ganador manualmente por número de ticket"""
    try:
        rifa = Rifa.objects.get(id=rifa_id)
        ticket = Ticket.objects.get(rifa=rifa, number=ticket_number, confirmed=True)
        
        # Asignar como ganador
        rifa.winner_ticket = ticket
        rifa.save()
        
        return ticket
    except (Rifa.DoesNotExist, Ticket.DoesNotExist):
        return None
    
# Agregar al final de admin2/crud.py

from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta

def obtener_reporte_ventas(fecha_inicio=None, fecha_fin=None, rifa_id=None):
    """Genera reporte de ventas con métricas clave."""
    qs = Compra.objects.filter(estado='CONFIRMADO')
    
    if fecha_inicio:
        qs = qs.filter(creado_en__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(creado_en__lte=fecha_fin)
    if rifa_id:
        qs = qs.filter(rifa_id=rifa_id)
    
    # Métricas generales
    total_ventas = qs.aggregate(
        total_compras=Count('id'),
        total_tickets=Sum('cantidad'),
        total_ingresos=Sum('monto')
    )
    
    # Ventas por rifa
    ventas_por_rifa = qs.values(
        'rifa__titulo',
        'rifa__id'
    ).annotate(
        compras=Count('id'),
        tickets_vendidos=Sum('cantidad'),
        ingresos=Sum('monto')
    ).order_by('-ingresos')
    
    # Ventas por método de pago
    ventas_por_metodo = qs.values('metodo_pago').annotate(
        compras=Count('id'),
        ingresos=Sum('monto')
    ).order_by('-ingresos')
    
    return {
        'totales': total_ventas,
        'por_rifa': list(ventas_por_rifa),
        'por_metodo': list(ventas_por_metodo),
        'periodo': {
            'inicio': fecha_inicio,
            'fin': fecha_fin
        }
    }


def obtener_reporte_rifas():
    """Genera reporte del estado de todas las rifas."""
    rifas = Rifa.objects.all().prefetch_related('tickets')
    
    reporte = []
    for rifa in rifas:
        tickets_vendidos = rifa.tickets.filter(confirmed=True).count()
        tickets_pendientes = rifa.tickets.filter(confirmed=False).count()
        ingresos = Compra.objects.filter(
            rifa=rifa, 
            estado='CONFIRMADO'
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        porcentaje_venta = (tickets_vendidos / rifa.total_tickets * 100) if rifa.total_tickets > 0 else 0
        
        estado = 'finalizada' if getattr(rifa, 'winner_ticket', None) else (
            'activa' if timezone.now().date() <= rifa.fecha_sorteo else 'pendiente_sorteo'
        )
        
        reporte.append({
            'id': rifa.id,
            'titulo': rifa.titulo,
            'fecha_sorteo': rifa.fecha_sorteo,
            'total_tickets': rifa.total_tickets,
            'tickets_vendidos': tickets_vendidos,
            'tickets_pendientes': tickets_pendientes,
            'porcentaje_venta': round(porcentaje_venta, 2),
            'ingresos': float(ingresos),
            'precio_ticket': float(rifa.precio),
            'estado': estado,
            'tiene_ganador': getattr(rifa, 'winner_ticket', None) is not None
        })
    
    return reporte


def obtener_reporte_participantes(rifa_id=None):
    """Genera reporte de participantes."""
    from app1.models import Participante, Ticket
    
    qs = Ticket.objects.filter(confirmed=True).select_related('participante', 'rifa')
    
    if rifa_id:
        qs = qs.filter(rifa_id=rifa_id)
    
    # Participantes con más tickets
    top_participantes = qs.values(
        'participante__nombre',
        'participante__identificacion',
        'participante__telefono'
    ).annotate(
        total_tickets=Count('id'),
        rifas_participadas=Count('rifa', distinct=True)
    ).order_by('-total_tickets')[:10]
    
    return {
        'top_participantes': list(top_participantes),
        'total_participantes': qs.values('participante').distinct().count()
    }


def obtener_estadisticas_dashboard():
    """Genera estadísticas para el dashboard principal."""
    now = timezone.now()
    hoy = now.date()
    hace_7_dias = now - timedelta(days=7)
    hace_30_dias = now - timedelta(days=30)
    
    # Rifas activas
    rifas_activas = Rifa.objects.filter(
        fecha_sorteo__gte=hoy
    ).exclude(
        winner_ticket__isnull=False
    ).count()
    
    # Ventas hoy
    ventas_hoy = Compra.objects.filter(
        estado='CONFIRMADO',
        creado_en__date=hoy
    ).aggregate(
        total=Count('id'),
        ingresos=Sum('monto')
    )
    
    # Ventas últimos 7 días
    ventas_semana = Compra.objects.filter(
        estado='CONFIRMADO',
        creado_en__gte=hace_7_dias
    ).aggregate(
        total=Count('id'),
        ingresos=Sum('monto'),
        tickets=Sum('cantidad')
    )
    
    # Ventas últimos 30 días
    ventas_mes = Compra.objects.filter(
        estado='CONFIRMADO',
        creado_en__gte=hace_30_dias
    ).aggregate(
        total=Count('id'),
        ingresos=Sum('monto'),
        tickets=Sum('cantidad')
    )
    
    # Compras pendientes
    compras_pendientes = Compra.objects.filter(estado='PENDIENTE').count()
    
    # Próximos sorteos
    proximos_sorteos = Rifa.objects.filter(
        fecha_sorteo__gte=hoy,
        fecha_sorteo__lte=hoy + timedelta(days=7)
    ).exclude(
        winner_ticket__isnull=False
    ).count()
    
    return {
        'rifas_activas': rifas_activas,
        'ventas_hoy': ventas_hoy,
        'ventas_semana': ventas_semana,
        'ventas_mes': ventas_mes,
        'compras_pendientes': compras_pendientes,
        'proximos_sorteos': proximos_sorteos
    }