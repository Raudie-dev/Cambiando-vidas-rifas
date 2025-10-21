from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('compra/<int:rifa_id>/', views.compra_rifa, name='compra_rifa'),
    path('tickets_status/<int:rifa_id>/', views.tickets_status, name='tickets_status'),
]