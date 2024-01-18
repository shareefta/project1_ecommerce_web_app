from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from .models import *
from category.models import Category
from category.forms import CategoryForm
from store.models import Product, Variant
from store.forms import ProductForm, VariantForm
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from .helper import MessageHandler
import random
from django.contrib.auth import login
from carts.views import _cart_id
from carts.models import Cart, CartItem
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
            username = email.split("@")[0]

            # Create an Account instance
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email,
                                               username=username, password=password)

            # Now, create a Profile instance
            profile = Profile.objects.create(user=user, phone_number=phone_number)

            messages.success(request, 'Registration Successful.')
            return redirect('login_user')
    else:
        form = RegistrationForm()
    context = {
        'form' : form
    }
    return render(request, 'accounts/register.html', context)

def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            password = form.cleaned_data['password']

            user = AccountUser.objects.create_user_account(full_name=full_name, email=email, phone_number=phone_number, password=password)
            user.save()
            profile = Profile.objects.create(user=user, phone_number=request.POST['phone_number'])
            profile.save()
            messages.success(request, 'Registration Successful.')
            return redirect('login_user')
    else:
        form = UserRegistrationForm()
    context = {
        'form' : form
    }
    return render(request, 'accounts/register_user.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_user(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        # Check if a profile with the given phone number exists
        profile = Profile.objects.filter(phone_number=phone_number).first()
        if not profile:
            messages.error(request, "Mobile Number does not exist")
            return redirect('register')
        # Retrieve the associated User object
        user = profile.user

        if not user.is_active:
            messages.error(request, "User is blocked. Please contact support.")
            return redirect('login_user')
        # Generate OTP
        otp = random.randint(1000, 9999)

        # Update the existing profile with the new OTP
        profile.otp = f'{otp}'
        profile.save()

        # Your messagehandler logic here (send OTP via message)
        messagehandler = MessageHandler(request.POST['phone_number'], otp).send_otp_via_message()
        red = redirect(f'otp/{profile.uid}/')
        return red
    return render(request, 'accounts/login_user.html')

def otp_verify(request, uid):
    if request.method == "POST":
        otp = request.POST.get('otp')
        try:
            profile = Profile.objects.get(uid=uid)
        except Profile.DoesNotExist:
            return HttpResponse("Profile not found", status=404)
        if otp == profile.otp:
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
                login(request, profile.user)
                request.session['profile_user_id'] = profile.user.id
                messages.success(request, 'Logged in successfully')
                url = request.META.get('HTTP_REFERER')
                try:
                    if url:
                        query = requests.utils.urlparse(url).query
                        params = dict(x.split('=') for x in query.split('&'))
                        if 'next' in params:
                            nextPage = params['next']
                            return redirect(nextPage)
                except:
                    return redirect('dashboard')
            return redirect('login_user')
        return messages.error(request, "Wrong OTP!. Please Enter Correct OTP.")
    return render(request, "accounts/otp.html", {'uid': uid})

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
    orders = Order.objects.all()
    return render(request, 'admin/order-list.html', {'orders' : orders})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def change_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        form = ChangeStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('order_list')
    else:
        form = ChangeStatusForm(instance=order)

    return render(request, 'admin/change-order-status.html', {'form': form, 'order_id': order_id})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_admin')
def cancel_order(request, order_id):
    order_to_delete = Order.objects.filter(id=order_id)
    order_to_delete.delete()

    return redirect('order_list')


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
                return redirect('change_password')
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
    subtotal = 0
    for i in order_detail:
        subtotal += i.product_price * i.quantity
    context = {
        'order_detail' : order_detail,
        'order' : order,
        'subtotal' : subtotal,
    }
    return render(request, 'accounts/order-detail.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='login_user')
def user_cancel_order(request, order_id):
    order_to_delete = Order.objects.filter(id=order_id)
    order_to_delete.delete()

    return redirect('my_orders')

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