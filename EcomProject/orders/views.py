from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Order, OrderProduct, Payment
from carts.models import CartItem
from store.models import Product
import datetime
from datetime import date
from django.contrib import messages
import uuid
from accounts.models import Address
from paypal.standard.forms import PayPalPaymentsForm
from django.urls import reverse
from accounts.forms import AddressForm



# Create your views here.

@login_required(login_url='login_user')
def add_address_checkout(request):
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
            return redirect('checkout')
    else:
        form = AddressForm()

    context = {
        'form': form
    }
    return render(request, 'orders/add-address-checkout.html', context)

def place_order(request, quantity=0, total=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')

    order_address = None

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':

        order_address_id = request.POST.get('selected_address', None)

        data = Order()
        data.user = current_user
        data.order_total = grand_total
        data.tax = tax
        data.ip = request.META.get('REMOTE_ADDR')
        data.save()

        if order_address_id:
            # Retrieve the address associated with the order
            order_address = Address.objects.get(id=order_address_id)
            data.address = order_address
            data.save()

        # #Generate Order Number:
        yr = int(date.today().strftime('%Y'))
        mt = int(date.today().strftime('%m'))
        dt = int(date.today().strftime('%d'))
        d = date(yr, mt, dt)
        current_date = d.strftime("%Y%m%d")
        order_number = current_date + str(data.id)
        data.order_number = order_number
        data.save()

        order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

        context = {
            'order_address': order_address,
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total
        }
        return render(request, 'orders/place-order.html', context)
    else:
        return HttpResponse('Error!')

def make_payments(request, order_id, order_total=None):
    current_user = request.user

    # Retrieve the order using the given order_id and user
    order = get_object_or_404(Order, id=order_id, user=current_user, is_ordered=False)

    if request.method == 'POST':
        if order and order.status == 'New':
            payment_method = request.POST.get('paymentMethod')

            # Perform different actions based on the selected payment method
            if payment_method == 'CashOnDelivery':
                # If payment method is Cash On Delivery, update the order status
                order.status = 'Accepted'
                order.is_ordered = True
                order.save()

                # Create a new Payment instance with a unique payment_id
                payment_id = uuid.uuid4().hex
                payment = Payment.objects.create(
                    user=current_user,
                    payment_id=payment_id,
                    amount_paid=order.order_total,
                    status='Completed'
                )

                order.payment = payment
                order.save()

                # Move cart item to OrderProduct Table:
                cart_items = CartItem.objects.filter(user=request.user)

                for item in cart_items:
                    orderproduct = OrderProduct()
                    orderproduct.order_id = order.id
                    orderproduct.payment = payment
                    orderproduct.user_id = request.user.id
                    orderproduct.product_id = item.product_id
                    orderproduct.quantity = item.quantity
                    orderproduct.product_price = item.product.price
                    orderproduct.ordered = True
                    orderproduct.save()

                    cart_item = CartItem.objects.get(id=item.id)
                    product_variant = cart_item.variant.all()
                    orderproduct = OrderProduct.objects.get(id=orderproduct.id)
                    orderproduct.variant.set(product_variant)
                    orderproduct.save()

                    # Reduce the stock of product sold:
                    product = Product.objects.get(id=item.product_id)
                    product.stock -= item.quantity
                    product.save()

                # Clear Cart:
                CartItem.objects.filter(user=request.user).delete()

                messages.success(request, 'Order placed successfully.')
                return redirect('orders:order_confirmation', order_id=order.id)

            elif payment_method == 'PayPal':
                host = request.get_host()

                paypal_checkout = {
                    'business': settings.PAYPAL_RECEIVER_EMAIL,
                    'amount': order.order_total,
                    'invoice': uuid.uuid4(),
                    'currency_code': 'USD',
                    'notify_url': f"http://{host}{reverse('paypal-ipn')}",
                    'return_url': f"http://{host}{reverse('orders:paypal_payment_success', kwargs={'order_id': order.id})}",
                    'cancel_url': f"http://{host}{reverse('orders:paypal_payment_failed', kwargs={'order_id': order.id})}",
                }

                paypal_payment = PayPalPaymentsForm(initial=paypal_checkout)
                context = {
                    'order': order,
                    'paypal': paypal_payment
                }

                return render(request, 'paypal/paypal-checkout.html', context)

            else:
                # Handle other payment methods or show an error message
                messages.error(request, 'Select a valid payment method.')
        else:
            # Handle the case where the order does not exist or is not in a suitable state for payment
            messages.error(request, 'Invalid order or order not in a valid state for payment.')
            return redirect('home')

    return render(request, 'orders/place-order.html', {'order': order})

def paypal_payment_success(request, order_id):
    # order = get_object_or_404(Order, id=order_id)
    current_user = request.user

    # Retrieve the order using the given order_id and user
    order = get_object_or_404(Order, id=order_id, user=current_user, is_ordered=False)

    # update the order status
    order.status = 'Accepted'
    order.is_ordered = True
    order.save()

    # Create a new Payment instance with a unique payment_id
    payment_id = uuid.uuid4().hex
    payment = Payment.objects.create(
        user=current_user,
        payment_id=payment_id,
        amount_paid=order.order_total,
        status='Completed'
    )

    order.payment = payment
    order.save()

    # Move cart item to OrderProduct Table:
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variant = cart_item.variant.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variant.set(product_variant)
        orderproduct.save()

        # Reduce the stock of product sold:
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    # Clear Cart:
    CartItem.objects.filter(user=request.user).delete()

    messages.success(request, 'Order placed successfully.')
    return redirect('orders:order_confirmation', order_id=order.id)

    # return render(request, 'paypal/paypal-payment-success.html', {'order': order})

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order-confirmation.html', {'order': order})

def paypal_payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'paypal/paypal-payment-failed.html', {'order': order})

@login_required(login_url='login_admin')
def order_detail_admin(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)

    total_product = []
    subtotal = 0

    for item in order_detail:
        product_total = item.product_price * item.quantity
        subtotal += product_total
        total_product.append({'item': item, 'total': product_total})

    context = {
        'order_detail': total_product,
        'order': order,
        'subtotal': subtotal,
    }
    return render(request, 'admin/order-detail-admin.html', context)

from datetime import datetime, timedelta

@login_required(login_url='login_admin')
def sales_report(request):
    # Calculate the start and end of the current day
    current_date = datetime.now()
    start_of_day = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

    # Filter OrderProduct objects for the current day
    orders = Order.objects.filter(created_at__range=[start_of_day, end_of_day])

    # Calculate the sum of order amount for the current day
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                            'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current day
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'current_date' : current_date,
        'orders': orders,
        'total_order_amount' : total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/daily-sales-report.html', context)

@login_required(login_url='login_admin')
def weekly_sales_report(request):

    # Calculate the start and end of the current week
    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Filter OrderProduct objects for the current week
    orders = Order.objects.filter(created_at__range=[start_of_week, end_of_week])

    # Calculate the sum of order amount for the current day
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current day
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_week' : start_of_week,
        'end_of_week' : end_of_week,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/weekly-sales-report.html', context)

@login_required(login_url='login_admin')
def monthly_sales_report(request):
    # Calculate the start and end of the current month
    current_date = datetime.now()
    start_of_month = current_date.replace(day=1)
    end_of_month = start_of_month + timedelta(days=32)
    end_of_month = end_of_month.replace(day=1) - timedelta(days=1)

    # Filter OrderProduct objects for the current month
    orders = Order.objects.filter(created_at__range=[start_of_month, end_of_month])

    # Calculate the sum of order amount for the current month
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current day
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_month' : start_of_month,
        'end_of_month' : end_of_month,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/monthly-sales-report.html', context)

@login_required(login_url='login_admin')
def yearly_sales_report(request):
    # Calculate the start and end of the current year
    current_date = datetime.now()
    start_of_year = current_date.replace(month=1, day=1)
    end_of_year = start_of_year.replace(year=start_of_year.year + 1) - timedelta(days=1)

    # Filter OrderProduct objects for the current year
    orders = Order.objects.filter(created_at__range=[start_of_year, end_of_year])

    # Calculate the sum of order amount for the current year
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current day
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_year' : start_of_year,
        'end_of_year' : end_of_year,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/yearly-sales-report.html', context)

