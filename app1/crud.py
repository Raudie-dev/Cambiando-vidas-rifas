from .models import Rifa, Participante, Ticket, Compra
from .models import PaymentMethod
from .models import PaymentMethodField
from django.db import transaction


def obtener_rifas():
    return Rifa.objects.all().prefetch_related('images')


def obtener_rifa(rifa_id):
    return Rifa.objects.prefetch_related('images').get(id=rifa_id)


def crear_participante(identificacion, nombre, email=''):
    participante, created = Participante.objects.get_or_create(identificacion=identificacion, defaults={'nombre': nombre, 'email': email})
    changed = False
    if participante.nombre != nombre:
        participante.nombre = nombre
        changed = True
    if email and participante.email != email:
        participante.email = email
        changed = True
    # note: telefono will be set by the caller if provided via crear_compra
    if changed:
        participante.save()
    return participante


def crear_compra(rifa, participante, cantidad, metodo_pago='', comprobante=None, referencia='', monto=None, telefono=None):
    # verifica disponibilidad
    if cantidad > rifa.tickets_available:
        raise ValueError('No hay suficientes tickets disponibles')

    # crear compra en estado PENDIENTE; reservar números (crear tickets con confirmed=False)
    # if telefono provided, ensure participante.telefono is saved
    if telefono:
        participante.telefono = telefono
        participante.save()

    compra = Compra.objects.create(rifa=rifa, participante=participante, cantidad=cantidad, metodo_pago=metodo_pago, referencia=referencia, monto=(monto or 0))
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


def crear_metodo_pago(nombre, detalles='', activo=True):
    metodo = PaymentMethod.objects.create(nombre=nombre, detalles=detalles, activo=activo)
    return metodo


def obtener_metodos():
    return PaymentMethod.objects.filter(activo=True).prefetch_related('fields').order_by('-creado_en')


def obtener_metodo(metodo_id):
    return PaymentMethod.objects.get(id=metodo_id)


def crear_metodo_con_campos(nombre, campos):
    """campos: lista de tuplas (field_name, field_value)"""
    metodo = PaymentMethod.objects.create(nombre=nombre, activo=True)
    for idx, (fname, fval) in enumerate(campos):
        PaymentMethodField.objects.create(metodo=metodo, field_name=fname, field_value=fval, orden=idx)
    return metodo


def obtener_todos_metodos():
    """Devuelve todos los métodos (incluyendo inactivos) para uso administrativo."""
    return PaymentMethod.objects.all().prefetch_related('fields').order_by('-creado_en')


def actualizar_metodo(metodo_id, nombre=None, detalles=None, activo=None):
    """Actualizar campos simples de un PaymentMethod."""
    metodo = PaymentMethod.objects.get(id=metodo_id)
    changed = False
    if nombre is not None and metodo.nombre != nombre:
        metodo.nombre = nombre
        changed = True
    if detalles is not None and metodo.detalles != detalles:
        metodo.detalles = detalles
        changed = True
    if activo is not None and metodo.activo != activo:
        metodo.activo = activo
        changed = True
    if changed:
        metodo.save()
    return metodo


def actualizar_metodo_con_campos(metodo_id, nombre=None, campos=None, activo=None):
    """Actualizar método y reemplazar sus campos.

    campos: lista de tuplas (field_name, field_value)
    """
    metodo = actualizar_metodo(metodo_id, nombre=nombre, detalles=None, activo=activo)
    if campos is not None:
        # eliminar campos existentes y crear los nuevos en orden
        PaymentMethodField.objects.filter(metodo=metodo).delete()
        for idx, (fname, fval) in enumerate(campos):
            PaymentMethodField.objects.create(metodo=metodo, field_name=fname, field_value=fval, orden=idx)
    return metodo


def desactivar_metodo(metodo_id):
    """Marcar método como inactivo en lugar de eliminarlo."""
    metodo = PaymentMethod.objects.get(id=metodo_id)
    metodo.activo = False
    metodo.save()
    return metodo


def eliminar_metodo(metodo_id):
    """Eliminar permanentemente un método y sus campos."""
    metodo = PaymentMethod.objects.get(id=metodo_id)
    metodo.delete()
    return True
