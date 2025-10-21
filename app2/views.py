from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from .models import User_admin
from . import crud as crud_rifas
from . import crud as admin_crud
from app1 import crud as app1_crud


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
    # En el panel admin mostramos todos los métodos (activos e inactivos)
    app_methods = app1_crud.obtener_todos_metodos()
    return render(request, 'control.html', {'rifas': rifas, 'app_methods': app_methods})


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