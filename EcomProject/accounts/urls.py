from django.urls import path
from . import views

urlpatterns = [

    #ADMIN
    path('register/', views.register, name="register"),
    path('login_admin/', views.login_admin, name="login_admin"),
    path('dashboard_admin', views.dashboard_admin, name='dashboard_admin'),
    path('logout_admin/', views.logout_admin, name="logout_admin"),

    #USER MANAGEMENT
    path('users_list', views.users_list, name="users_list"),
    path('toggle_user_status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),


    # CATEGORY MANAGEMENT
    path('category_list', views.category_list, name="category_list"),
    path('category_add', views.category_add, name="category_add"),
    path('category_update/<int:category_id>', views.category_update, name="category_update"),
    path('category_delete/<slug:id>', views.category_delete, name="category_delete"),

    # PRODUCT MANAGEMENT
    path('product_list', views.product_list, name="product_list"),
    path('product_add', views.product_add, name="product_add"),
    path('product_update/<int:product_id>', views.product_update, name="product_update"),
    path('product_delete/<slug:id>', views.product_delete, name="product_delete"),

    # VARIANT MANAGEMENT
    path('variant_list', views.variant_list, name="variant_list"),
    path('variant_add', views.variant_add, name='variant_add'),
    path('variant_update/<int:variant_id>', views.variant_update, name="variant_update"),
    path('variant_delete/<int:variant_id>', views.variant_delete, name="variant_delete"),

    # ORDER MANAGEMENT
    path('order_list', views.order_list, name="order_list"),
    path('change_order_status/<int:order_id>/', views.change_order_status, name='change_order_status'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),

    #USER
    path('register_user',views.register_user, name='register_user'),
    path('login_user',views.login_user, name='login_user'),
    path('otp/<str:uid>/', views.otp_verify, name='otp'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout_user/', views.logout_user, name="logout_user"),
    path('my_orders/', views.my_orders, name='my_orders'),
    path('edit_profile', views.edit_profile, name='edit_profile'),
    path('change_password', views.change_password, name='change_password'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('user_cancel_order/<int:order_id>/', views.user_cancel_order, name='user_cancel_order'),
    path('address_list/', views.address_list, name='address_list'),
    path('add_address/', views.add_address, name='add_address'),
    path('edit_address/<int:address_id>/', views.edit_address, name='edit_address')
]
