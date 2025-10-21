from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import Rifa, Participante, Ticket, Compra
from django.db import transaction
from . import crud as crud_app


@require_http_methods(['GET', 'POST'])
def index(request):
    """GET: mostrar rifas y estado.
    POST: procesar compra de tickets para una rifa.
    Form fields expected for POST: rifa_id, identificacion, nombre, cantidad
    """
    if request.method == 'POST':
        # keep backward compatibility if index had POST for direct purchase
        rifa_id = request.POST.get('rifa_id')
        return redirect('compra_rifa', rifa_id=rifa_id)

    # GET
    rifas = crud_app.obtener_rifas()
    return render(request, 'index.html', {'rifas': rifas})



@require_http_methods(['GET', 'POST'])
def compra_rifa(request, rifa_id):
    rifa = get_object_or_404(Rifa, pk=rifa_id)

    if request.method == 'POST':
        identificacion = request.POST.get('identificacion', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        cantidad = int(request.POST.get('cantidad') or 0)
        metodo_pago = request.POST.get('metodo_pago', '').strip()
        referencia = request.POST.get('referencia', '').strip()
        comprobante = request.FILES.get('comprobante')

        if not (identificacion and nombre and cantidad > 0 and metodo_pago):
            messages.error(request, 'Completa todos los campos requeridos.')
            return redirect('compra_rifa', rifa_id=rifa.id)

        try:
            participante = crud_app.crear_participante(identificacion, nombre, email)
            compra = crud_app.crear_compra(rifa, participante, cantidad, metodo_pago=metodo_pago, comprobante=comprobante, referencia=referencia)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('compra_rifa', rifa_id=rifa.id)

        messages.success(request, f'Compra registrada con ID {compra.id}. Estado: {compra.estado}. Esperando confirmación administrativa.')
        return redirect('index')

    # GET: mostrar formulario de compra y métodos de pago
    metodos_pago = crud_app.obtener_metodos()
    return render(request, 'compra_rifa.html', {'rifa': rifa, 'metodos_pago': metodos_pago})


@require_http_methods(['GET'])
def tickets_status(request, rifa_id):
    """Endpoint JSON: devuelve el estado de la última compra del participante para la rifa
    y los números de ticket asignados si la compra está confirmada.
    Parámetros GET: identificacion
    """
    identificacion = request.GET.get('identificacion', '').strip()
    if not identificacion:
        return JsonResponse({'error': 'identificacion requerida'}, status=400)

    try:
        participante = Participante.objects.get(pk=identificacion)
    except Participante.DoesNotExist:
        return JsonResponse({'status': 'NO_PARTICIPANTE', 'message': 'Participante no encontrado'})

    compra = Compra.objects.filter(rifa_id=rifa_id, participante=participante).order_by('-creado_en').first()
    if not compra:
        return JsonResponse({'status': 'NO_COMPRA', 'message': 'No hay compras para ese participante en esta rifa'})

    if compra.estado != 'CONFIRMADO':
        return JsonResponse({'status': compra.estado, 'message': f'Compra encontrada con estado {compra.estado}'})

    tickets_qs = Ticket.objects.filter(rifa_id=rifa_id, participante=participante).order_by('number')
    tickets = list(tickets_qs.values_list('number', flat=True))
    return JsonResponse({'status': 'CONFIRMADO', 'tickets': tickets})
