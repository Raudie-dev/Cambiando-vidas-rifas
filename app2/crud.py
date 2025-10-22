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
            RifaImage.objects.create(rifa=rifa, image=f)
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