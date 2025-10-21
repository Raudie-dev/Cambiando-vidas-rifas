from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('control/', views.control, name='control'),
    path('compras/', views.compras, name='compras'),
]