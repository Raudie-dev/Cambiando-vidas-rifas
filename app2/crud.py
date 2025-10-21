from app1.models import Rifa, RifaImage
from app1.models import Compra
from app1 import crud as app1_crud


def crear_rifa(titulo, fecha_sorteo, total_tickets=100, descripcion='', fotos=None):
    rifa = Rifa(titulo=titulo, fecha_sorteo=fecha_sorteo, total_tickets=total_tickets, descripcion=descripcion)
    rifa.save()

    # Guardar hasta 3 imágenes
    if fotos:
        count = 0
        for f in fotos:
            if count >= 3:
                break
            RifaImage.objects.create(rifa=rifa, image=f)
            count += 1

    return rifa


def obtener_rifas():
    return Rifa.objects.all().prefetch_related('images')


def eliminar_rifa(rifa_id):
    Rifa.objects.filter(id=rifa_id).delete()


def actualizar_rifa(rifa_id, titulo=None, fecha_sorteo=None, total_tickets=None, descripcion=None, foto=None):
    rifa = Rifa.objects.get(id=rifa_id)
    if titulo is not None:
        rifa.titulo = titulo
    if fecha_sorteo is not None:
        rifa.fecha_sorteo = fecha_sorteo
    if total_tickets is not None:
        rifa.total_tickets = total_tickets
    if descripcion is not None:
        rifa.descripcion = descripcion
    if foto is not None:
        rifa.foto = foto
    rifa.save()
    return rifa


def obtener_compras_pendientes():
    return Compra.objects.filter(estado='PENDIENTE').select_related('rifa', 'participante')


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