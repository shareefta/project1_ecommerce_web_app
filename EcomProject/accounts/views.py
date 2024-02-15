import secrets

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.crypto import get_random_string
from django.urls import reverse

from .forms import *
from .models import *
from category.models import Category
from category.forms import CategoryForm
from store.models import Product, Variant
from store.forms import ProductForm, VariantForm, ProductOfferForm
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from .helper import MessageHandler
import random
from django.contrib.auth import login, logout
from carts.views import _cart_id
from carts.models import Cart, CartItem, Coupons, UserCoupons
from orders.models import Order, OrderProduct
from orders.forms import ChangeStatusForm
import requests


# Create your views here.

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Create an Account instance
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, phone_number=phone_number, email=email,
                                               password=password)
            user.save()

            # # user activation
            # otp = ''.join(secrets.choice('0123456789') for _ in range(4))
            # profile = Profile.objects.create(user=user, otp=f'{otp}')
            # profile.save()
            # user_details = {
            #     'uid': profile.uid,
            #     'phone_number': profile.user.phone_number,
            #
            # }
            # request.session['user_details'] = user_details
            # messagehandler = MessageHandler(request.POST['phone_number'],otp).send_otp_via_message()
            # red = redirect(reverse('otp_verify', args=[str(profile.uid)]))
            # # red = redirect(f'otp/{profile.uid}/')
            # red.set_cookie("can_otp_enter", True, max_age=60)
            # return red
            messages.success(request, 'Registration Successful.')
            return redirect('login_user')
    else:
        form = RegistrationForm()
    context = {
        'form' : form
    }
    return render(request, 'accounts/register.html', context)


# user registration_otp_verify
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# @never_cache
# def otp_verify(request, uid):
#     if request.method == "POST":
#         otp = request.POST.get('otp')
#         try:
#             profile = Profile.objects.filter(uid=uid).first()
#         except Profile.DoesNotExist:
#             return HttpResponse("Profile not found", status=404)
#         if request.COOKIES.get('can_otp_enter') != None:
#             if otp == profile.otp:
#                 if profile.user is not None:
#                     profile.user.session = {'profile.user.id': profile.user.id}
#                     profile.user.is_active = True
#                     profile.user.save()
#                     request.session['key3'] = 3
#                     messages.success(request, 'Your Account has been activated.You can log in now')
#                     return redirect("login")
#                 return redirect('register')
#             messages.error(request, 'You have entered wrong OTP.Try again')
#             return redirect(request.path)
#         messages.error(request, '60 seconds over.Try again')
#         return redirect(request.path)
#     return render(request, "accounts/otp-verify-login.html", {'uid': uid})


# user login
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def login_user(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        # Check if a profile with the given phone number exists
        user = Account.objects.filter(email=email).first()
        if not user:
            messages.error(request, "User does not exist.")
            return redirect('login')
        if not user.is_active:
            messages.error(request,
                           "Your account has been temporarily blocked. Please contact support for further assistance.")
            return redirect('login')
        profile = Profile.objects.get(user=user)
        otp = ''.join(secrets.choice('0123456789') for _ in range(4))
        profile.otp = otp
        profile.save()
        user_details = {
            'profile_email': profile.user.email,
            'phone_number': profile.user.phone_number,
        }
        request.session['user_details'] = user_details
        messagehandler = MessageHandler(profile.user.phone_number, otp).send_otp_via_message()
        red = redirect('otp_verify_login', uid=str(profile.uid))
        red.set_cookie("can_otp_enter", True, max_age=60)
        return red
    return render(request, 'accounts/login_user.html')

def otp_verify_login(request, uid):
    if request.method == "POST":
        try:
            profile = Profile.objects.get(otp=request.POST['otp'])
        except:
            messages.error(request, 'You have entered wrong OTP.Try again')
            return redirect(request.path)
        if request.COOKIES.get('can_otp_enter') != None:
            if profile.otp == request.POST['otp']:
                if profile.user is not None:
                    try:
                        cart = Cart.objects.get(cart_id=_cart_id(request))
                        is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                        if is_cart_item_exists:
                            cart_items = CartItem.objects.filter(cart=cart)
                            #Getting the product variants by cart id
                            product_variant = []
                            for cart_item in cart_items:
                                variant = cart_item.variant.all()
                                product_variant.append(list(variant))

                            #Get the cart items from the user to access his product variants
                            cart_items = CartItem.objects.filter(user=profile.user)
                            ex_variant_list = []
                            id = []
                            for cart_item in cart_items:
                                existing_variant = cart_item.variant.all()
                                ex_variant_list.append(list(existing_variant))
                                id.append(cart_item.id)

                            for p_variant in product_variant:
                                if p_variant in ex_variant_list:
                                    index = ex_variant_list.index(p_variant)
                                    item_id = id[index]
                                    item = CartItem.objects.get(id=item_id)
                                    item.quantity += 1
                                    item.user = profile.user
                                    item.save()
                                else:
                                    cart_items = CartItem.objects.filter(cart=cart)
                                    for cart_item in cart_items:
                                        cart_item.user = profile.user
                                        cart_item.save()
                    except:
                        pass
                    auth.login(request, profile.user)
                    profile.user.session = {'profile.user.id': profile.user.id}
                    profile.user.save()
                    profile = {
                        'id': profile.id,
                        'first_name': profile.user.first_name
                    }
                    context = {'profile': profile}
                    request.session['profile'] = profile
                    return render(request, 'home.html', {'profile': profile})
                return redirect('login_user')
            else:
                messages.error(request, 'You have entered wrong OTP.Try again')
                return redirect(request.path)
        messages.error(request, '60 seconds over.Try again')
        return redirect(request.path)
    return render(request, "accounts/otp-verify-login.html", {'uid': uid})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def logout_user(request):
    auth.logout(request)
    messages.success(request, 'Lougout Successful')
    return redirect('login_user')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_admin(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('dashboard_admin')
        else:
            messages.error(request, "Invalid Credentials")
            return redirect('login_admin')
    return render(request, 'accounts/login.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def logout_admin(request):
    auth.logout(request)
    messages.success(request, 'Lougout Successful')
    return redirect('login_admin')
    pass

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count =orders.count()
    context = {
        'orders_count' : orders_count,
    }
    return render(request, 'accounts/dashboard.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
def dashboard_admin(request):
    return render(request, 'accounts/dashboard_admin.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def category_list(request):
    category_list = Category.objects.all()
    return render(request, 'admin/category_list.html', {'category_list' : category_list})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category_name = form.cleaned_data['category_name']
            slug = form.cleaned_data['slug']
            description = form.cleaned_data['description']
            category_image = form.cleaned_data['category_image']

            category = Category.objects.create(category_name=category_name, slug=slug, description=description, category_image=category_image)
            category.save()
            messages.success(request, 'Category Added Successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    context = {
        'form': form
    }
    return render(request, 'admin/category_create.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')

def category_update(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'admin/category_update.html', {'form': form, 'category_id': category_id})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def category_delete(request, id):
    category_to_delete = Category.objects.filter(id=id)
    category_to_delete.delete()

    return redirect('category_list')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def product_list(request):
    product_list = Product.objects.all()
    return render(request, 'admin/product_list.html', {'product_list' : product_list})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product_name = form.cleaned_data['product_name']
            slug = form.cleaned_data['slug']
            description = form.cleaned_data['description']
            price = form.cleaned_data['price']
            stock = form.cleaned_data['stock']
            category = form.cleaned_data['category']
            product_image = form.cleaned_data['product_image']

            product = Product.objects.create(product_name=product_name, slug=slug, description=description, price=price,
                                             stock=stock, category=category, product_image=product_image)
            product.save()
            messages.success(request, 'Product Added Successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()
    context = {
        'form': form
    }
    return render(request, 'admin/product_create.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def product_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'admin/product_update.html', {'form': form, 'product_id': product_id})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def product_delete(request, id):
    product_to_delete = Product.objects.filter(id=id)
    product_to_delete.delete()

    return redirect('product_list')

def variant_list(request):
    variant_list = Variant.objects.all()
    return render(request, 'admin/variant_list.html', {'variant_list': variant_list})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def variant_add(request):
    if request.method == 'POST':
        form = VariantForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            variant_category = form.cleaned_data['variant_category']
            variant_value = form.cleaned_data['variant_value']

            variant = Variant.objects.create(product=product, variant_category=variant_category, variant_value=variant_value)
            variant.save()
            messages.success(request, 'Variant Added Successfully.')
            return redirect('variant_list')
    else:
        form = VariantForm()
    context = {
        'form': form
    }
    return render(request, 'admin/variant_create.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def variant_update(request, variant_id):
    variant = get_object_or_404(Variant, pk=variant_id)

    if request.method == 'POST':
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            return redirect('variant_list')
    else:
        form = VariantForm(instance=variant)
    return render(request, 'admin/variant_update.html', {'form': form, 'variant_id': variant_id})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def variant_delete(request, variant_id):
    variant_to_delete = Variant.objects.filter(id=variant_id)
    variant_to_delete.delete()

    return redirect('variant_list')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def users_list(request):
    profiles = Profile.objects.all()
    return render(request, 'admin/users_list.html', {'profiles': profiles})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def toggle_user_status(request, user_id):
    user = get_object_or_404(Account, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect('users_list')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'admin/order-list.html', {'orders' : orders})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def change_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    old_status = order.status
    if request.method == 'POST':
        form = ChangeStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            new_status = form.cleaned_data['status']
            if new_status == "Cancelled" or old_status == "Order Confirmed":
                user = order.user
                user.wallet += order.order_total
                user.save()
            elif new_status == "Return Received" or old_status == "Cancelled":
                user = order.user
                user.wallet += order.order_total
                user.save()

            # Update product stock based on the new status
            update_product_stock(order, old_status, new_status)
            return redirect('order_list')
    else:
        form = ChangeStatusForm(instance=order)
    return render(request, 'admin/change-order-status.html', {'form': form, 'order_id': order_id})

def update_product_stock(order, old_status, new_status):
    # Function to update product stock based on order status change
    if old_status == "Order Confirmed" and new_status == "Cancelled":
        # Order status changed from New to Cancelled, increase product stock
        for order_product in order.products.all():
            increase_stock(order_product.product, order_product.quantity)

    elif old_status == "Cancelled" and new_status == "Order Confirmed":
        # Order status changed from Cancelled to Accepted, decrease product stock
        for order_product in order.products.all():
            decrease_stock(order_product.product, order_product.quantity)

    elif  new_status == "Return Received":
        # Order status changed from New to Cancelled, increase product stock
        for order_product in order.products.all():
            increase_stock(order_product.product, order_product.quantity)

def increase_stock(product, quantity):
    # Function to increase product stock
    product.stock += quantity
    product.save()

def decrease_stock(product, quantity):
    # Function to decrease product stock
    if product.stock >= quantity:
        product.stock -= quantity
        product.save()

@login_required(login_url='login_admin')
def coupon_list(request):
    coupons = Coupons.objects.all()

    context = {'coupons': coupons}
    return render(request, 'admin/coupon-list.html', context)

@login_required(login_url='login_admin')
def product_offer_list(request):
    products = Product.objects.filter(is_available=True)

    offer_produtcts = []
    for product in products:
        if product.offer_percentage > 0:
            offer_product = product
            offer_produtcts.append(offer_product)

    context = { 'offer_products' : offer_produtcts}

    return render(request, 'admin/product-offer-list.html', context)

@login_required(login_url='login_admin')
def add_product_offer(request):
    if request.method == 'POST':
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            product_name = form.cleaned_data['product_name']
            offer_percentage = form.cleaned_data['offer_percentage']

            form.save()
            messages.success(request, 'Product Offer Added Successfully.')
            return redirect('product_offer_list')
    else:
        form = ProductOfferForm()
    context = {
        'form': form
    }
    return render(request, 'admin/add-product-offer.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def user_cancel_order(request, order_id):
    order_to_cancel = Order.objects.get(id=order_id)
    order_to_cancel.status = 'Cancelled'
    order_to_cancel.is_cancelled = True
    order_to_cancel.save()

    # Add the amount of order total to user's wallet
    order = get_object_or_404(Order, id=order_id)
    user = order.user
    user.wallet += order.order_total
    user.save()

    # Increase product stock for each item in the canceled order
    for order_product in order_to_cancel.products.all():
        product = order_product.product
        product.stock += order_product.quantity
        product.save()

    return redirect('my_orders')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders' : orders
    }
    return render(request, 'accounts/my-orders.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your Profile Updated Successfully')
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    context = {
        'user_form' : user_form,
        'profile_form' : profile_form,
        'userprofile' : userprofile,
    }
    return render(request, 'accounts/edit-profile.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']
        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                messages.success(request, 'Password Updated Successfully')
                auth.logout(request)
                # messages.success(request, 'Lougout Successful')
                return redirect('login_user')
            else:
                messages.error(request,'Enter Valid Current Password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password Does Not Match')
            return redirect('change_password')
    return render(request, 'accounts/change-password.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def order_detail(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)

    total_product = []
    subtotal = 0
    total_product_discount = 0

    for item in order_detail:
        product_total = item.product_price * item.quantity
        subtotal += product_total
        total_product.append({'item': item, 'total': product_total})
        discount_price = (item.product.offer_percentage * item.product.price) / 100
        total_product_discount += discount_price * item.quantity

    context = {
        'order_detail': total_product,
        # 'total_product': total_product,
        'order': order,
        'subtotal': subtotal,
        'tax': order.tax,
        'grand_total': subtotal + order.tax,
        'coupon_discount': order.coupon_discount,
        'total_product_discount': total_product_discount,
    }

    return render(request, 'accounts/order-detail.html', context)

@login_required(login_url='login_user')
def my_coupons(request):
    if request.user.is_authenticated:
        coupons = Coupons.objects.all()
        user = request.user

        coupon_statuses = []

        for coupon in coupons:
            is_used = UserCoupons.objects.filter(coupon=coupon, user=user, is_used=True).exists()
            coupon_statuses.append("Used" if is_used else "Active")

        coupon_data = zip(coupons, coupon_statuses)

        context = {'coupon_data': coupon_data}
        return render(request, 'accounts/my-coupons.html', context)
    else:
        return redirect('login_user')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def address_list(request):
    address = Address.objects.filter(user=request.user)
    context = {
        'address' : address
    }
    return render(request, 'accounts/address-list.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            # Get the current user
            current_user = request.user

            # Extract data from the form
            full_name = form.cleaned_data['full_name']
            phone_number = form.cleaned_data['phone_number']
            address_line_1 = form.cleaned_data['address_line_1']
            address_line_2 = form.cleaned_data['address_line_2']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            country = form.cleaned_data['country']
            zipcode = form.cleaned_data['zipcode']

            # Create and save the address with the current user
            address = Address.objects.create(
                user=current_user,
                full_name=full_name,
                phone_number=phone_number,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                state=state,
                country=country,
                zipcode=zipcode
            )

            messages.success(request, 'Address Added Successfully.')
            return redirect('address_list')
    else:
        form = AddressForm()

    context = {
        'form': form
    }
    return render(request, 'accounts/add-address.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('address_list')
    else:
        form = AddressForm(instance=address)
    return render(request, 'accounts/edit-address.html', {'form': form, 'address_id': address_id})

def forgot_password(request):
    if request.method == "POST":
        first_name = request.POST['first_name']
        email = request.POST['email']
        phone_number = request.POST['phone_number']
        try:
            user = Account.objects.get(email=email)
            # phone_number = Profile.objects.get(phone_number=phone_number)
        except:
            return HttpResponse("User doesnt exist")

        otp = get_random_string(12)
        messagehandler = MessageHandler(user.phone_number, otp).send_otp_via_message()
        user.set_password(otp)
        user.save()
        logout(request)
        messages.success(request, 'The code to reset your password has been sent to your mobile number.')
        return redirect('login_user')

    return render(request, 'accounts/forgot-password-user.html')

def add_money_wallet(request):
    if request.method == "POST":
        amount = float(request.POST.get('amount', 0))
        user = request.user
        user.wallet += amount
        user.save()
        messages.success(request, 'Money added Successfully')
        return redirect(request.path)
    return render(request,'accounts/my-wallet.html')