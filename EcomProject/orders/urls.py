from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # path('add_billing_address/', views.add_billing_address, name='add_billing_address'),
    path('place_order/', views.place_order, name='place_order'),
    path('make_payments/<int:order_id>/', views.make_payments, name='make_payments'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
]
