from .models import Rifa, Participante, Ticket, Compra
from django.db import transaction


def obtener_rifas():
    return Rifa.objects.all().prefetch_related('images')


def obtener_rifa(rifa_id):
    return Rifa.objects.prefetch_related('images').get(id=rifa_id)


def crear_participante(identificacion, nombre, email=''):
    participante, _ = Participante.objects.get_or_create(identificacion=identificacion, defaults={'nombre': nombre, 'email': email})
    if participante.nombre != nombre:
        participante.nombre = nombre
        participante.save()
    return participante


def crear_compra(rifa, participante, cantidad, metodo_pago='', comprobante=None, referencia=''):
    # verifica disponibilidad
    if cantidad > rifa.tickets_available:
        raise ValueError('No hay suficientes tickets disponibles')

    # crear compra en estado PENDIENTE; reservar números (crear tickets con confirmed=False)
    compra = Compra.objects.create(rifa=rifa, participante=participante, cantidad=cantidad, metodo_pago=metodo_pago, referencia=referencia)
    if comprobante:
        compra.comprobante = comprobante
        compra.save()

    # reservar números inmediatamente (no confirmados)
    assigned = []
    used = set(Ticket.objects.filter(rifa=rifa).values_list('number', flat=True))
    num = 1
    while len(assigned) < cantidad and num <= rifa.total_tickets:
        if num not in used:
            ticket = Ticket.objects.create(rifa=rifa, participante=participante, number=num, compra=compra, confirmed=False)
            assigned.append(ticket)
            used.add(num)
        num += 1

    if len(assigned) < cantidad:
        # rollback: eliminar tickets creados y la compra
        for t in assigned:
            t.delete()
        compra.delete()
        raise ValueError('No hay suficientes tickets disponibles al intentar reservar')

    return compra


def asignar_tickets_a_compra(compra):
    rifa = compra.rifa
    cantidad = compra.cantidad
    # Confirmar tickets previamente reservados (aquellos con compra=compracompra y confirmed=False)
    with transaction.atomic():
        reserved_qs = Ticket.objects.filter(compra=compra, confirmed=False).order_by('number')
        reserved_count = reserved_qs.count()
        if reserved_count < cantidad:
            raise ValueError('No se encuentran los tickets reservados suficientes para confirmar')

        # marcar como confirmed
        reserved_qs.update(confirmed=True)
        compra.estado = 'CONFIRMADO'
        compra.save()

    return list(reserved_qs)
