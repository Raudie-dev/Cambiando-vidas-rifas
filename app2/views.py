from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import User_admin
from . import crud as crud_rifas
from . import crud as admin_crud


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
        # El formulario de creación viene con campos: titulo, fecha_sorteo, total_tickets, descripcion, foto
        if 'eliminar_id' in request.POST:
            eliminar_id = request.POST.get('eliminar_id')
            crud_rifas.eliminar_rifa(eliminar_id)
            messages.success(request, 'Rifa eliminada correctamente')
            return redirect('control')

        titulo = request.POST.get('titulo', '').strip()
        fecha_sorteo = request.POST.get('fecha_sorteo')
        total_tickets = request.POST.get('total_tickets')
        descripcion = request.POST.get('descripcion', '').strip()
        fotos = request.FILES.getlist('fotos') or request.FILES.getlist('foto') or None

        if not (titulo and fecha_sorteo and total_tickets):
            messages.error(request, 'Completa título, fecha y total de tickets')
            return redirect('control')

        try:
            total_tickets = int(total_tickets)
        except ValueError:
            messages.error(request, 'Total de tickets debe ser un número')
            return redirect('control')

        crud_rifas.crear_rifa(titulo=titulo, fecha_sorteo=fecha_sorteo, total_tickets=total_tickets, descripcion=descripcion, fotos=fotos)
        messages.success(request, 'Rifa creada correctamente')
        return redirect('control')

    rifas = crud_rifas.obtener_rifas()
    return render(request, 'control.html', {'rifas': rifas})


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

    pendientes = admin_crud.obtener_compras_pendientes()
    return render(request, 'compras.html', {'compras': pendientes})