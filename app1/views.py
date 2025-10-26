from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import Rifa, Participante, Ticket, Compra
from django.db import transaction
from . import crud as crud_app
from decimal import Decimal, InvalidOperation
from bot import send_compra_message


@require_http_methods(['GET', 'POST'])
def index(request):
    rifas = Rifa.objects.all().prefetch_related('images', 'tickets')
    
    rifas_con_info = []
    for rifa in rifas:
        # Calcular tickets vendidos y disponibles
        tickets_sold = rifa.tickets.count()
        tickets_available = rifa.total_tickets - tickets_sold
        
        # Verificar si tiene ganador
        has_winner = rifa.winner_ticket is not None
        
        rifas_con_info.append({
            'id': rifa.id,
            'titulo': rifa.titulo,
            'descripcion': rifa.descripcion,
            'precio': rifa.precio,
            'fecha_sorteo': rifa.fecha_sorteo,
            'total_tickets': rifa.total_tickets,
            'tickets_sold': tickets_sold,
            'tickets_available': tickets_available,
            'images': rifa.images.all(),
            'has_winner': has_winner,  # Nuevo campo
            'winner_info': rifa.winner_ticket.participante.nombre if has_winner else None,  # Info del ganador si existe
        })
    
    return render(request, 'index.html', {'rifas': rifas_con_info})



@require_http_methods(['GET', 'POST'])
def compra_rifa(request, rifa_id):
    rifa = get_object_or_404(Rifa, pk=rifa_id)

    if request.method == 'POST':
        identificacion = request.POST.get('identificacion', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        metodo_pago = request.POST.get('metodo_pago', '').strip()
        referencia = request.POST.get('referencia', '').strip()
        comprobante = request.FILES.get('comprobante')

        # parse cantidad safely
        try:
            cantidad = int(request.POST.get('cantidad') or 0)
        except (ValueError, TypeError):
            messages.error(request, 'Cantidad inválida')
            return redirect('compra_rifa', rifa_id=rifa.id)

        if not (identificacion and nombre and cantidad > 0 and metodo_pago):
            messages.error(request, 'Completa todos los campos requeridos.')
            return redirect('compra_rifa', rifa_id=rifa.id)

        # validate telefono if provided: allow digits, +, spaces, hyphens, parentheses, min length 7
        if telefono:
            import re
            if not re.match(r'^[0-9+()\-\s]{7,}$', telefono):
                messages.error(request, 'Número de teléfono inválido. Use solo dígitos, +, espacios, guiones o paréntesis.')
                return redirect('compra_rifa', rifa_id=rifa.id)

        # calcular total usando el precio de la rifa (Decimal)
        try:
            total = (rifa.precio or Decimal('0')) * Decimal(cantidad)
        except (InvalidOperation, TypeError):
            total = Decimal('0')

        try:
            participante = crud_app.crear_participante(identificacion, nombre, email)
            compra = crud_app.crear_compra(rifa, participante, cantidad, metodo_pago=metodo_pago, comprobante=comprobante, referencia=referencia, monto=total, telefono=telefono)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('compra_rifa', rifa_id=rifa.id)
        except Exception as e:
            # capture unexpected errors during creation
            print('Error creando compra:', e)
            messages.error(request, 'Error interno al procesar la compra. Intenta nuevamente.')
            return redirect('compra_rifa', rifa_id=rifa.id)

        # Enviar mensaje al grupo de Telegram, pero no fallar la compra si el bot falla
        try:
            send_compra_message(compra)
        except Exception as e:
            print('Warning: fallo al enviar notificación bot:', e)
        # mostrar total en el mensaje de confirmación (formateado)
        try:
            total_str = f"{total:.2f}"
        except Exception:
            total_str = str(total)

        messages.success(request, f'Compra registrada. Estado: {compra.estado}. Esperando confirmación administrativa.')
        return redirect('index')

    # GET: mostrar formulario de compra y métodos de pago
    metodos_pago = crud_app.obtener_metodos()
    # pasar el precio de la rifa al template para cálculo en cliente si se desea
    return render(request, 'compra_rifa.html', {'rifa': rifa, 'metodos_pago': metodos_pago, 'precio_rifa': rifa.precio})


@require_http_methods(['GET'])
def tickets_status(request, rifa_id):
    """Endpoint JSON: devuelve TODAS las compras y tickets del participante para la rifa
    Parámetros GET: identificacion
    """
    identificacion = request.GET.get('identificacion', '').strip()
    if not identificacion:
        return JsonResponse({'error': 'identificación requerida'}, status=400)

    try:
        participante = Participante.objects.get(pk=identificacion)
    except Participante.DoesNotExist:
        return JsonResponse({'status': 'NO_PARTICIPANTE', 'message': 'Participante no encontrado'})

    # Obtener TODAS las compras del participante en esta rifa
    compras = Compra.objects.filter(
        rifa_id=rifa_id, 
        participante=participante
    ).order_by('-creado_en')
    
    if not compras.exists():
        return JsonResponse({'status': 'NO_COMPRA', 'message': 'No hay compras para ese participante en esta rifa'})

    # Preparar datos de todas las compras
    compras_data = []
    tickets_totales = []
    
    for compra in compras:
        # Obtener tickets de esta compra específica
        tickets_compra = Ticket.objects.filter(
            rifa_id=rifa_id, 
            participante=participante,
            compra=compra
        ).order_by('number')
        
        tickets_numeros = list(tickets_compra.values_list('number', flat=True))
        tickets_totales.extend(tickets_numeros)
        
        compras_data.append({
            'compra_id': compra.id,
            'fecha_compra': compra.creado_en.strftime("%d/%m/%Y %H:%M"),
            'cantidad': compra.cantidad,
            'estado': compra.estado,
            'metodo_pago': compra.metodo_pago,
            'referencia': compra.referencia or 'N/A',
            'tickets': tickets_numeros,
            'monto_total': str(compra.monto) if compra.monto else '0.00'
        })

    return JsonResponse({
        'status': 'SUCCESS',
        'participante': {
            'identificacion': participante.identificacion,
            'nombre': participante.nombre,
            'email': participante.email or 'No proporcionado'
        },
        'compras': compras_data,
        'tickets_totales': sorted(tickets_totales),
        'total_compras': len(compras_data),
        'total_tickets': len(tickets_totales)
    })
