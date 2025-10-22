from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('control/', views.control, name='control'),
    path('compras/', views.compras, name='compras'),
    path('historial-compras/', views.historial_compras, name='historial_compras'),
    path('sorteo/<int:rifa_id>/', views.sorteo, name='sorteo'),
    path('sorteos/', views.sorteos, name='sorteos'),
]