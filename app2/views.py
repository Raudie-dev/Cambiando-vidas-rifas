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
            # collect per-slot edit files (support both list input 'fotos_edit_list' and individual slots)
            fotos_edit_slots = []
            # prefer the list-style input generated by the modal JS
            fotos_edit_list = request.FILES.getlist('fotos_edit_list') if hasattr(request, 'FILES') else []
            if fotos_edit_list:
                # keep up to 3
                fotos_edit_slots = fotos_edit_list[:3]
            else:
                # fallback to older per-slot names
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
        # collect create files: prefer list-style 'fotos_list' from the modal JS,
        # but keep backward compatibility with 'fotos_1/2/3' inputs.
        fotos_slots = []
        if hasattr(request, 'FILES'):
            fotos_slots = request.FILES.getlist('fotos_list') or []
        if not fotos_slots:
            fotos_slots = [
                request.FILES.get('fotos_1'),
                request.FILES.get('fotos_2'),
                request.FILES.get('fotos_3'),
            ]
        # build fotos list filtering out empty slots and limit to 3
        fotos = [f for f in fotos_slots if f][:3]

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

    # Serializar rifas para que el JS del template pueda mostrar imágenes y usar el
    # modal de edición como visor. Incluimos URLs de las imágenes y campos relevantes.
    rifas_list = []
    for r in rifas:
        images = []
        try:
            for img in r.images.all():
                # image.url produce la ruta relativa bajo MEDIA_URL; es suficiente para el frontend
                try:
                    images.append(img.image.url)
                except Exception:
                    # ignore missing files
                    continue
        except Exception:
            images = []

        rifas_list.append({
            'id': r.id,
            'titulo': r.titulo,
            'descripcion': r.descripcion,
            'fecha_sorteo': r.fecha_sorteo.isoformat() if getattr(r, 'fecha_sorteo', None) else None,
            'total_tickets': r.total_tickets,
            'precio': float(r.precio) if getattr(r, 'precio', None) is not None else 0,
            'images': images,
            'tickets_sold': getattr(r, 'tickets', None) and r.tickets.count() or 0,
        })

    rifas_json = json.dumps(rifas_list, cls=DjangoJSONEncoder)

    context = {
        'rifas': rifas,
        'app_methods': app_methods,
        'rifas_json': rifas_json,
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

    # VERIFICACIÓN ADICIONAL: Si ya tiene ganador, no permitir otro sorteo
    if getattr(rifa, 'winner_ticket', None) and not request.POST.get('force'):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': 'Esta rifa ya tiene un ganador asignado. No se puede realizar otro sorteo.'})
        messages.error(request, 'Esta rifa ya tiene un ganador asignado. No se puede realizar otro sorteo.')
        return redirect(f"{reverse('sorteos')}?open={rifa_id}")

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
                return JsonResponse({'ok': False, 'message': 'No hay tickets confirmados o la rifa ya tiene ganador.'})
            messages.error(request, 'No se pudo seleccionar un ganador (falta de tickets confirmados o rifa ya tiene ganador).')
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

    # Obtener el parámetro de filtro
    selected_rifa = request.GET.get('rifa_id')
    
    # Filtrar rifas si se seleccionó una específica
    if selected_rifa:
        rifas_qs = Rifa.objects.filter(id=selected_rifa).order_by('-fecha_sorteo').prefetch_related('tickets', 'images')
    else:
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

    # Obtener todas las rifas para el dropdown
    todas_las_rifas = Rifa.objects.all().order_by('titulo')

    return render(request, 'sorteos.html', {
        'rifas': rifas_info,
        'rifas_filtro': todas_las_rifas,  # Cambié el nombre para evitar confusión
        'selected_rifa': selected_rifa
    })

def asignar_ganador_manual(request, rifa_id):
    """Asignar ganador manualmente por número de ticket"""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': 'Debe iniciar sesión primero'})
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')

    if request.method == 'POST' and 'ticket_number' in request.POST:
        ticket_number = request.POST.get('ticket_number', '').strip()
        
        try:
            rifa = Rifa.objects.get(id=rifa_id)
            
            # VERIFICACIÓN: Si ya tiene ganador, no permitir asignar otro
            if getattr(rifa, 'winner_ticket', None):
                message = 'Esta rifa ya tiene un ganador asignado. No se puede asignar otro ganador.'
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'message': message})
                messages.error(request, message)
                return redirect(f"{reverse('sorteos')}?open={rifa_id}")
            
            # VERIFICACIÓN: Solo permitir en la fecha del sorteo
            now = timezone.localtime(timezone.now())
            today = now.date()
            can_draw = (getattr(rifa, 'fecha_sorteo', None) == today)
            
            if not can_draw:
                message = 'La asignación manual solo puede realizarse en la fecha programada del sorteo.'
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'message': message})
                messages.error(request, message)
                return redirect(f"{reverse('sorteos')}?open={rifa_id}")
            
            ticket = Ticket.objects.get(rifa=rifa, number=ticket_number, confirmed=True)
            
            # Asignar como ganador
            rifa.winner_ticket = ticket
            rifa.save()
            
            # Construir respuesta
            winner_text = f'Ticket #{ticket.number} — {ticket.participante.nombre}'
            telefono = getattr(ticket.participante, 'telefono', None)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True, 
                    'winner': {
                        'id': ticket.id, 
                        'number': ticket.number, 
                        'nombre': ticket.participante.nombre, 
                        'identificacion': ticket.participante.identificacion, 
                        'telefono': telefono
                    }, 
                    'winner_text': winner_text, 
                    'rifa_id': rifa_id
                })
            
            messages.success(request, f'Ganador asignado manualmente: {winner_text}')
            return redirect(f"{reverse('sorteos')}?open={rifa_id}&winner={ticket.id}")
            
        except Rifa.DoesNotExist:
            message = 'Rifa no encontrada'
        except Ticket.DoesNotExist:
            message = 'Ticket no encontrado o no confirmado'
        except Exception as e:
            message = f'Error al asignar ganador: {str(e)}'
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': message})
        messages.error(request, message)
    
    return redirect(f"{reverse('sorteos')}?open={rifa_id}")

# Agregar a admin2/views.py

def reportes(request):
    """Vista principal de reportes con dashboard."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    
    # Obtener estadísticas del dashboard
    stats = admin_crud.obtener_estadisticas_dashboard()
    
    # Obtener todas las rifas para el selector
    rifas = Rifa.objects.all().order_by('-fecha_sorteo')
    
    context = {
        'stats': stats,
        'rifas': rifas,
    }
    
    return render(request, 'reportes.html', context)


def reporte_ventas(request):
    """Vista de reporte de ventas con filtros."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    rifa_id = request.GET.get('rifa_id')
    
    # Convertir fechas si existen
    if fecha_inicio:
        from datetime import datetime
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            fecha_inicio = None
    
    if fecha_fin:
        from datetime import datetime
        try:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            # Incluir todo el día
            fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
        except ValueError:
            fecha_fin = None
    
    # Generar reporte
    reporte = admin_crud.obtener_reporte_ventas(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        rifa_id=rifa_id
    )
    
    # Obtener rifas para el selector
    rifas = Rifa.objects.all().order_by('-fecha_sorteo')
    
    context = {
        'reporte': reporte,
        'rifas': rifas,
        'filtros': {
            'fecha_inicio': request.GET.get('fecha_inicio', ''),
            'fecha_fin': request.GET.get('fecha_fin', ''),
            'rifa_id': rifa_id
        }
    }
    
    return render(request, 'reporte_ventas.html', context)


def reporte_rifas(request):
    """Vista de reporte de estado de rifas."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    
    reporte = admin_crud.obtener_reporte_rifas()
    
    # Calcular totales
    totales = {
        'total_rifas': len(reporte),
        'total_tickets': sum(r['total_tickets'] for r in reporte),
        'total_vendidos': sum(r['tickets_vendidos'] for r in reporte),
        'total_ingresos': sum(r['ingresos'] for r in reporte),
        'rifas_finalizadas': sum(1 for r in reporte if r['tiene_ganador']),
        'rifas_activas': sum(1 for r in reporte if r['estado'] == 'activa')
    }
    
    context = {
        'reporte': reporte,
        'totales': totales
    }
    
    return render(request, 'reporte_rifas.html', context)


def reporte_participantes(request):
    """Vista de reporte de participantes."""
    user_id = request.session.get('user_admin_id')
    if not user_id:
        messages.error(request, 'Debe iniciar sesión primero')
        return redirect('login')
    
    rifa_id = request.GET.get('rifa_id')
    reporte = admin_crud.obtener_reporte_participantes(rifa_id=rifa_id)
    
    # Obtener rifas para el selector
    rifas = Rifa.objects.all().order_by('-fecha_sorteo')
    
    context = {
        'reporte': reporte,
        'rifas': rifas,
        'rifa_id': rifa_id
    }
    
    return render(request, 'reporte_participantes.html', context)