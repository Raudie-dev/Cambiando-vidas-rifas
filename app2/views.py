from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import User_admin
from . import crud as crud_rifas
from . import crud as admin_crud
from django.core.serializers.json import DjangoJSONEncoder
import json
from app1 import crud as app1_crud
from app1.models import Rifa, Ticket
from django.utils import timezone
from django.urls import reverse
from django.http import JsonResponse
from . import crud as local_crud
import random


def login(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        password = request.POST.get('password', '')

        try:
            user = User_admin.objects.get(nombre=nombre)
            if user.bloqueado:
                messages.error(request, 'Usuario bloqueado')
            elif user.password == password or check_password(password, user.password):
                request.session['user_admin_id'] = user.id
                return redirect('control')
            else:
                messages.error(request, 'Contraseña incorrecta')
            return render(request, 'login.html')
        except User_admin.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return render(request, 'login.html')

    return render(request, 'login.html')


def control(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    try:
        user = User_admin.objects.get(id=user_id)
    except User_admin.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('login')

    # Manejar creación de rifa
    if request.method == 'POST':
        # Editar método de pago
        if 'editar_metodo' in request.POST:
            metodo_id = request.POST.get('editar_metodo_id')
            nombre = request.POST.get('metodo_nombre_edit', '').strip()
            field_names = request.POST.getlist('field_name_list')
            field_values = request.POST.getlist('field_value_list')
            campos = []
            for i, fname in enumerate(field_names):
                if fname.strip():
                    fval = field_values[i] if i < len(field_values) else ''
                    campos.append((fname.strip(), fval.strip()))
            if campos:
                app1_crud.actualizar_metodo_con_campos(metodo_id, nombre=nombre, campos=campos)
            else:
                app1_crud.actualizar_metodo(metodo_id, nombre=nombre)
            messages.success(request, 'Método actualizado')
            return redirect('control')

        # Eliminar método (desde el botón en la tabla)
        if 'eliminar_metodo_id' in request.POST:
            metodo_id = request.POST.get('eliminar_metodo_id')
            app1_crud.eliminar_metodo(metodo_id)
            messages.success(request, 'Método eliminado')
            return redirect('control')

        # Toggle activar/desactivar método
        if 'toggle_metodo_id' in request.POST:
            metodo_id = request.POST.get('toggle_metodo_id')
            activo_val = request.POST.get('activo')
            activo = True if activo_val in ('1', 'true', 'True') else False
            app1_crud.actualizar_metodo(metodo_id, activo=activo)
            messages.success(request, 'Estado del método actualizado')
            return redirect('control')

        # Crear método de pago desde modal
        if 'crear_metodo_pago' in request.POST:
            nombre = request.POST.get('metodo_nombre', '').strip()
            # recibir listas serializadas desde el modal
            field_names = request.POST.getlist('field_name_list')
            field_values = request.POST.getlist('field_value_list')
            detalles = ''
            if not nombre:
                messages.error(request, 'Nombre del método requerido')
                return redirect('control')
            # emparejar campos
            campos = []
            for i, fname in enumerate(field_names):
                if fname.strip():
                    fval = field_values[i] if i < len(field_values) else ''
                    campos.append((fname.strip(), fval.strip()))
            if campos:
                app1_crud.crear_metodo_con_campos(nombre=nombre, campos=campos)
            else:
                app1_crud.crear_metodo_pago(nombre=nombre, detalles=detalles)
            messages.success(request, 'Método de pago creado')
            return redirect('control')

        # El formulario de creación viene con campos: titulo, fecha_sorteo, total_tickets, descripcion, foto
        if 'eliminar_id' in request.POST:
            eliminar_id = request.POST.get('eliminar_id')
            crud_rifas.eliminar_rifa(eliminar_id)
            messages.success(request, 'Rifa eliminada correctamente')
            return redirect('control')

        # Editar rifa desde modal (permitir updates parciales — solo rifa_id es obligatorio)
        if 'editar_rifa' in request.POST:
            rifa_id = request.POST.get('editar_rifa_id')
            if not rifa_id:
                messages.error(request, 'Id de rifa requerido')
                return redirect('control')

            # Leer valores; si están vacíos los tratamos como None (no modificar)
            titulo_raw = request.POST.get('titulo_edit')
            titulo = titulo_raw.strip() if titulo_raw and titulo_raw.strip() != '' else None

            fecha_sorteo = request.POST.get('fecha_sorteo_edit') or None

            total_tickets_raw = request.POST.get('total_tickets_edit')
            total_tickets = None
            if total_tickets_raw is not None and total_tickets_raw != '':
                try:
                    total_tickets = int(total_tickets_raw)
                except ValueError:
                    messages.error(request, 'Total de tickets debe ser un número')
                    return redirect('control')

            descripcion_raw = request.POST.get('descripcion_edit')
            descripcion = descripcion_raw.strip() if descripcion_raw and descripcion_raw.strip() != '' else None

            precio_raw = request.POST.get('precio_edit')
            precio_val = None
            if precio_raw is not None and precio_raw != '':
                try:
                    precio_val = float(precio_raw)
                except ValueError:
                    messages.error(request, 'Precio inválido')
                    return redirect('control')

            # Llamar al CRUD pasando solo los valores (editar_rifa los ignorará si son None)
            # collect per-slot edit files (none if not provided)
            fotos_edit_slots = [
                request.FILES.get('fotos_edit_1'),
                request.FILES.get('fotos_edit_2'),
                request.FILES.get('fotos_edit_3'),
            ]
            crud_rifas.editar_rifa(rifa_id, titulo=titulo, fecha_sorteo=fecha_sorteo, total_tickets=total_tickets, descripcion=descripcion, precio=precio_val, fotos_edit_slots=fotos_edit_slots)
            messages.success(request, 'Rifa actualizada correctamente')
            return redirect('control')

        titulo = request.POST.get('titulo', '').strip()
        fecha_sorteo = request.POST.get('fecha_sorteo')
        total_tickets = request.POST.get('total_tickets')
        precio = request.POST.get('precio', '0')
        descripcion = request.POST.get('descripcion', '').strip()
        # collect per-slot create files
        fotos_slots = [
            request.FILES.get('fotos_1'),
            request.FILES.get('fotos_2'),
            request.FILES.get('fotos_3'),
        ]
        # build fotos list filtering out empty slots
        fotos = [f for f in fotos_slots if f]

        if not (titulo and fecha_sorteo and total_tickets):
            messages.error(request, 'Completa título, fecha y total de tickets')
            return redirect('control')

        try:
            total_tickets = int(total_tickets)
        except ValueError:
            messages.error(request, 'Total de tickets debe ser un número')
            return redirect('control')

        try:
            precio_val = float(precio) if precio is not None and precio != '' else 0.0
        except ValueError:
            messages.error(request, 'Precio inválido')
            return redirect('control')

        crud_rifas.crear_rifa(titulo=titulo, fecha_sorteo=fecha_sorteo, total_tickets=total_tickets, descripcion=descripcion, fotos=fotos, precio=precio_val)
        messages.success(request, 'Rifa creada correctamente')
        return redirect('control')

    rifas = crud_rifas.obtener_rifas()
    # En el panel admin mostramos todos los métodos (activos e inactivos)
    app_methods = app1_crud.obtener_todos_metodos()

    context = {
        'rifas': rifas,
        'app_methods': app_methods,
    }
    return render(request, 'control.html', context)


def compras(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    if request.method == 'POST':
        if 'confirmar_id' in request.POST:
            compra_id = request.POST.get('confirmar_id')
            try:
                compra, assigned = admin_crud.confirmar_compra(compra_id)
                messages.success(request, f'Compra {compra_id} confirmada. Tickets asignados: {", ".join(str(t.number) for t in assigned)}')
            except Exception as e:
                messages.error(request, f'Error al confirmar compra: {e}')
            return redirect('compras')
        if 'rechazar_id' in request.POST:
            compra_id = request.POST.get('rechazar_id')
            admin_crud.rechazar_compra(compra_id)
            messages.info(request, f'Compra {compra_id} rechazada')
            return redirect('compras')

    # permitir filtrar por rifa mediante GET ?rifa_id=NN
    selected_rifa = request.GET.get('rifa_id')
    pendientes = admin_crud.obtener_compras_pendientes(rifa_id=selected_rifa)
    # pasar lista de rifas para el dropdown
    rifas = admin_crud.obtener_rifas()
    return render(request, 'compras.html', {'compras': pendientes, 'rifas': rifas, 'selected_rifa': selected_rifa})


def historial_compras(request):
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    # permitir filtrar por rifa mediante GET ?rifa_id=NN
    selected_rifa = request.GET.get('rifa_id')
    historial = admin_crud.obtener_historial_compras(rifa_id=selected_rifa)
    # pasar lista de rifas para el dropdown
    rifas = admin_crud.obtener_rifas()
    return render(request, 'historial_compras.html', {'compras': historial, 'rifas': rifas, 'selected_rifa': selected_rifa})


def sorteo(request, rifa_id):
    """Página para realizar el sorteo manualmente en el día de la rifa.

    Solo permite ejecutar el sorteo si la fecha actual (en timezone del proyecto)
    coincide con `rifa.fecha_sorteo`.
    """
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    try:
        rifa = Rifa.objects.prefetch_related('tickets').get(id=rifa_id)
    except Rifa.DoesNotExist:
        messages.error(request, 'Rifa no encontrada')
        return redirect('control')

    # comparar solo la parte fecha usando timezone local
    now = timezone.localtime(timezone.now())
    today = now.date()

    can_draw = (getattr(rifa, 'fecha_sorteo', None) == today)

    # listar tickets confirmados de la rifa
    tickets = Ticket.objects.filter(rifa=rifa, confirmed=True).order_by('number')

    # If the admin opened the singular sorteo URL via GET, redirect to the
    # `sorteos` list page and instruct it to open the modal for this rifa.
    if request.method == 'GET':
        # include `open` so the list page can auto-open the modal for this rifa
        return redirect(f"{reverse('sorteos')}?open={rifa_id}")

    if request.method == 'POST' and 'do_draw' in request.POST:
        if not can_draw:
            # AJAX => JSON, otherwise redirect with message
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'message': 'El sorteo solo puede ejecutarse en la fecha programada de la rifa'})
            messages.error(request, 'El sorteo solo puede ejecutarse en la fecha programada de la rifa')
            return redirect(f"{reverse('sorteos')}?open={rifa_id}")

        force = request.POST.get('force', '') == '1'
        winner = local_crud.perform_sorteo(rifa_id, force=force)
        if not winner:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'message': 'No hay tickets confirmados o la rifa no existe.'})
            messages.error(request, 'No se pudo seleccionar un ganador (falta de tickets confirmados o rifa inexistente).')
            return redirect(f"{reverse('sorteos')}?open={rifa_id}")

        # build a short winner descriptor to show in UI
        winner_text = f'Ticket #{winner.number} — {winner.participante.nombre}'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # include telefono if available
            telefono = getattr(winner.participante, 'telefono', None) if getattr(winner, 'participante', None) else None
            return JsonResponse({'ok': True, 'winner': {'id': winner.id, 'number': winner.number, 'nombre': winner.participante.nombre, 'identificacion': winner.participante.identificacion, 'telefono': telefono}, 'winner_text': winner_text, 'rifa_id': rifa_id})

        messages.success(request, f'Ganador seleccionado: {winner_text} ({winner.participante.identificacion})')
        return redirect(f"{reverse('sorteos')}?open={rifa_id}&winner={winner.id}")

    # Legacy: the single 'sorteo.html' view is deprecated; redirect to the
    # list page which contains the inline modal.
    return redirect(f"{reverse('sorteos')}?open={rifa_id}")


def sorteos(request):
    """Lista simple de rifas con enlace a la página de sorteo para cada una."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    rifas_qs = Rifa.objects.all().order_by('-fecha_sorteo').prefetch_related('tickets', 'images')
    now = timezone.localtime(timezone.now())
    today = now.date()

    rifas_info = []
    for r in rifas_qs:
        try:
            tickets_sold = r.tickets.count()
        except Exception:
            tickets_sold = 0
        can_draw = (getattr(r, 'fecha_sorteo', None) == today)
        winner = None
        if getattr(r, 'winner_ticket', None):
            # try to present minimal winner info
            wt = r.winner_ticket
            winner = {
                'number': wt.number,
                'nombre': getattr(wt.participante, 'nombre', ''),
                'identificacion': getattr(wt.participante, 'identificacion', ''),
                'telefono': getattr(wt.participante, 'telefono', ''),
            }
        rifas_info.append({
            'id': r.id,
            'titulo': r.titulo,
            'fecha_sorteo': r.fecha_sorteo,
            'total_tickets': r.total_tickets,
            'tickets_sold': tickets_sold,
            'precio': r.precio,
            'can_draw': can_draw,
            'winner': winner,
        })

    return render(request, 'sorteos.html', {'rifas': rifas_info})