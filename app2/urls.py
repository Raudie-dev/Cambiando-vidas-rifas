from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('control/', views.control, name='control'),
    path('compras/', views.compras, name='compras'),
    path('historial-compras/', views.historial_compras, name='historial_compras'),
    path('sorteo/<int:rifa_id>/', views.sorteo, name='sorteo'),
    path('sorteos/', views.sorteos, name='sorteos'),
    path('asignar-ganador/<int:rifa_id>/', views.asignar_ganador_manual, name='asignar_ganador'),
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/ventas/', views.reporte_ventas, name='reporte_ventas'),
    path('reportes/rifas/', views.reporte_rifas, name='reporte_rifas'),
    path('reportes/participantes/', views.reporte_participantes, name='reporte_participantes'),
    path('logout/', views.logout, name='logout'),
]
