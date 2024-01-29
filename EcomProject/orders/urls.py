from django.urls import path
from . import views


app_name = 'orders'

urlpatterns = [
    path('add_address_checkout', views.add_address_checkout, name='add_address_checkout'),

    path('place_order/', views.place_order, name='place_order'),
    path('make_payments/<int:order_id>/', views.make_payments, name='make_payments'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),

    path('paypal_payment_success/<int:order_id>/', views.paypal_payment_success, name='paypal_payment_success'),
    path('paypal_payment_failed/<int:order_id>/', views.paypal_payment_failed, name='paypal_payment_failed'),

    path('order_detail_admin/<int:order_id>/', views.order_detail_admin, name='order_detail_admin'),

    path('sales_report/', views.sales_report, name='sales_report'),
    path('weekly_sales_report/', views.weekly_sales_report, name='weekly_sales_report'),
    path('monthly_sales_report/', views.monthly_sales_report, name='monthly_sales_report'),
    path('yearly_sales_report/', views.yearly_sales_report, name='yearly_sales_report'),

]