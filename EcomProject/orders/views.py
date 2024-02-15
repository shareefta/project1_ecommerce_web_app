from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
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
from carts.models import Coupons, UserCoupons
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter


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

    user_addresses = Address.objects.filter(user=current_user)
    if not user_addresses:
        messages.error(request, "Please add at least one address before placing an order.")
        return redirect('orders:add_address_checkout')

    for cart_item in cart_items:
        if cart_item.product.offer_percentage > 0:
            discount_price = (cart_item.product.offer_percentage * cart_item.product.price) / 100
            cart_item.product.offer_price = cart_item.product.price - discount_price
            total += (cart_item.product.offer_price * cart_item.quantity)
            quantity += cart_item.quantity
        else:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity

    tax = (2 * total) / 100
    order_total = total
    grand_total = order_total + tax

    order_address = None

    if request.method == 'POST':

        order_address_id = request.POST.get('selected_address', None)

        data = Order()
        data.user = current_user
        data.order_total = order_total
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
            'tax': tax,
            'order_total': order_total,
            'grand_total': grand_total,
        }
        return redirect('orders:coupon', order_id=data.id)
        # return render(request, 'orders/place-order.html', context)
    else:
        return HttpResponse('Error!')


def coupon(request, order_id):
    coupons = Coupons.objects.all()
    user = request.user

    coupon_statuses = []

    for coupon in coupons:
        is_used = UserCoupons.objects.filter(coupon=coupon, user=user, is_used=True).exists()
        coupon_statuses.append("Used" if is_used else "Active")

    all_used = all(status == "Used" for status in coupon_statuses)

    if all_used:
        order = get_object_or_404(Order, id=order_id, user=user, is_ordered=False)
        context = {
            'order_address': order.address,
            'order': order,
            'cart_items': CartItem.objects.filter(user=user),
            'order_total': order.order_total,
            'tax': order.tax,
            'grand_total': order.order_total + order.tax,
            'wallet': user.wallet
        }
        return render(request, 'orders/place-order.html', context)
    else:
        order = get_object_or_404(Order, id=order_id, user=user, is_ordered=False)

        coupons = Coupons.objects.all()
        user = request.user

        coupon_statuses = []

        for coupon in coupons:
            is_used = UserCoupons.objects.filter(coupon=coupon, user=user, is_used=True).exists()
            coupon_statuses.append("Used" if is_used else "Active")

        coupon_data = zip(coupons, coupon_statuses)

        context = {
            'order_address': order.address,
            'order': order,
            'cart_items': CartItem.objects.filter(user=user),
            'order_total': order.order_total,
            'tax': order.tax,
            'grand_total': order.order_total + order.tax,
            'coupon_data': coupon_data,
        }
        return render(request, 'orders/apply-coupon.html', context)


def apply_coupon(request, order_id):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        # request.session['coupon_code'] = coupon_code

        try:
            coupon = Coupons.objects.get(coupon_code=coupon_code)
            order = Order.objects.get(id=order_id)
            user = request.user

            if coupon.valid_from <= timezone.now() <= coupon.valid_to:
                if order.order_total >= coupon.minimum_amount:
                    if coupon.is_used_by_user(request.user):
                        messages.warning(request, 'Coupon has already been used')
                    else:
                        order.coupon_discount = coupon.discount
                        updated_total = order.order_total - float(coupon.discount)
                        order.order_total = updated_total
                        order.save()

                        used_coupons = UserCoupons(user=request.user, coupon=coupon, is_used=True)
                        used_coupons.save()

                        #Calculation of Total Product Discount
                        cart_items = CartItem.objects.filter(user=request.user, is_active=True)
                        product_discount = 0
                        for cart_item in cart_items:
                            if cart_item.product.offer_percentage > 0:
                                discount_price = (cart_item.product.offer_percentage * cart_item.product.price) / 100
                                product_discount += discount_price * cart_item.quantity

                        context = {
                            'coupon_discount': order.coupon_discount,
                            'order_id': order.id,
                            'order_address': order.address,
                            'order': order,
                            'cart_items': CartItem.objects.filter(user=user),
                            'order_total': order.order_total,
                            'tax': order.tax,
                            'grand_total': order.order_total + order.tax,
                            'product_discount': product_discount,
                            'total_discount': order.coupon_discount + product_discount,
                            'wallet': user.wallet,
                        }
                        return render(request, 'orders/place-order.html', context)
                else:
                    messages.warning(request, 'Coupon is not applicable for order total')
            else:
                messages.warning(request, 'Coupon is not applicable for the current date')
        except ObjectDoesNotExist:
            messages.warning(request, 'Coupon code is invalid')
            return render(request, 'orders/place-order.html', {'order_id': order_id})

    # Redirect to the place order page if the request method is not POST
    return render(request, 'orders/place-order.html', {'order_id': order_id})


def make_payments(request, order_id):
    current_user = request.user

    # Retrieve the order using the given order_id and user
    order = get_object_or_404(Order, id=order_id, user=current_user, is_ordered=False)

    if request.method == 'POST':
        if order and order.status == 'Pending':
            payment_method = request.POST.get('paymentMethod')

            # Perform different actions based on the selected payment method
            if payment_method == 'Wallet':
                # If payment method is Wallet, update the order status
                user = request.user
                if user.wallet >= order.order_total:
                    user.wallet -= order.order_total
                    user.save()

                    order.status = 'Order Confirmed'
                    order.is_ordered = True
                    order.save()

                    # Create a new Payment instance with a unique payment_id
                    payment_id = uuid.uuid4().hex
                    payment = Payment.objects.create(
                        user=current_user,
                        payment_id=payment_id,
                        amount_paid=order.order_total + order.tax,
                        status='Completed'
                    )

                    order.payment = payment
                    order.save()

                    # Move cart item to OrderProduct Table:
                    cart_items = CartItem.objects.filter(user=request.user)

                    for item in cart_items:
                        if item.product.offer_percentage > 0:
                            orderproduct = OrderProduct()
                            orderproduct.order_id = order.id
                            orderproduct.payment = payment
                            orderproduct.user_id = request.user.id
                            orderproduct.product_id = item.product_id
                            orderproduct.quantity = item.quantity
                            orderproduct.tax = order.tax
                            orderproduct.ordered = True
                            discount_price = (item.product.offer_percentage * item.product.price) / 100
                            orderproduct.product_price = item.product.price - discount_price
                            orderproduct.product_discount = discount_price * item.quantity
                            orderproduct.save()
                        else:
                            orderproduct = OrderProduct()
                            orderproduct.order_id = order.id
                            orderproduct.payment = payment
                            orderproduct.user_id = request.user.id
                            orderproduct.product_id = item.product_id
                            orderproduct.quantity = item.quantity
                            orderproduct.product_price = item.product.price
                            orderproduct.tax = order.tax
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
                else:
                    messages.error(request, 'Wallet balance insufficient')
                    return redirect('checkout')

            elif payment_method == 'CashOnDelivery':
                # If payment method is Cash On Delivery, update the order status
                order.status = 'Order Confirmed'
                order.is_ordered = True
                order.save()

                # Create a new Payment instance with a unique payment_id
                payment_id = uuid.uuid4().hex
                payment = Payment.objects.create(
                    user=current_user,
                    payment_id=payment_id,
                    amount_paid=order.order_total + order.tax,
                    status='Completed'
                )

                order.payment = payment
                order.save()

                # Move cart item to OrderProduct Table:
                cart_items = CartItem.objects.filter(user=request.user)

                for item in cart_items:
                    if item.product.offer_percentage > 0:
                        orderproduct = OrderProduct()
                        orderproduct.order_id = order.id
                        orderproduct.payment = payment
                        orderproduct.user_id = request.user.id
                        orderproduct.product_id = item.product_id
                        orderproduct.quantity = item.quantity
                        orderproduct.tax = order.tax
                        orderproduct.ordered = True
                        discount_price = (item.product.offer_percentage * item.product.price) / 100
                        orderproduct.product_price = item.product.price - discount_price
                        orderproduct.product_discount = discount_price * item.quantity
                        orderproduct.save()
                    else:
                        orderproduct = OrderProduct()
                        orderproduct.order_id = order.id
                        orderproduct.payment = payment
                        orderproduct.user_id = request.user.id
                        orderproduct.product_id = item.product_id
                        orderproduct.quantity = item.quantity
                        orderproduct.product_price = item.product.price
                        orderproduct.tax = order.tax
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
    current_user = request.user

    # Retrieve the order using the given order_id and user
    order = get_object_or_404(Order, id=order_id, user=current_user, is_ordered=False)

    # update the order status
    order.status = 'Order Confirmed'
    order.is_ordered = True
    order.save()

    # Create a new Payment instance with a unique payment_id
    payment_id = uuid.uuid4().hex
    payment = Payment.objects.create(
        user=current_user,
        payment_id=payment_id,
        amount_paid=order.order_total + order.tax,
        status='Completed'
    )

    order.payment = payment
    order.save()

    # Move cart item to OrderProduct Table:
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        if item.product.offer_percentage > 0:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.quantity = item.quantity
            orderproduct.tax = order.tax
            orderproduct.ordered = True
            discount_price = (item.product.offer_percentage * item.product.price) / 100
            orderproduct.product_price = item.product.price - discount_price
            orderproduct.product_discount = discount_price * item.quantity
            orderproduct.save()
        else:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.quantity = item.quantity
            orderproduct.product_price = item.product.price
            orderproduct.tax = order.tax
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
    return render(request, 'admin/order-detail-admin.html', context)


from datetime import datetime, timedelta


@login_required(login_url='login_admin')
def sales_report(request):
    # Calculate the start and end of the current day
    current_date = datetime.now()
    start_of_day = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

    # Filter OrderProduct objects for the current day
    orders = Order.objects.filter(created_at__range=[start_of_day, end_of_day]).order_by('-created_at')

    # Calculate the sum of order amount for the current day
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current day
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'current_date': current_date,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/daily-sales-report.html', context)


@login_required(login_url='login_admin')
def weekly_sales_report(request):
    # Calculate the start and end of the current week
    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Filter OrderProduct objects for the week
    orders = Order.objects.filter(created_at__range=[start_of_week, end_of_week]).order_by('-created_at')

    # Calculate the sum of order amount for the week
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the week
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
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
    orders = Order.objects.filter(created_at__range=[start_of_month, end_of_month]).order_by('-created_at')

    # Calculate the sum of order amount for the current month
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current month
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_month': start_of_month,
        'end_of_month': end_of_month,
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
    orders = Order.objects.filter(created_at__range=[start_of_year, end_of_year]).order_by('-created_at')

    # Calculate the sum of order amount for the current year
    total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))[
                             'total_order_amount'] or 0

    # Calculate the sum of amount_paid for the current year
    total_amount_paid = orders.aggregate(total_amount_paid=Sum('payment__amount_paid'))['total_amount_paid'] or 0

    context = {
        'start_of_year': start_of_year,
        'end_of_year': end_of_year,
        'orders': orders,
        'total_order_amount': total_order_amount,
        'total_amount_paid': total_amount_paid,
    }

    return render(request, 'sales-report/yearly-sales-report.html', context)


# Generate a PDF Daily Sales Report
def sales_report_pdf(request):
    buf = io.BytesIO()
    # create canvas
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    # create a text object
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    current_date = datetime.now()
    start_of_day = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

    # Filter OrderProduct objects for the current day
    orders = Order.objects.filter(created_at__range=[start_of_day, end_of_day]).order_by('-created_at')

    # Define column widths
    serial_width = 10
    order_number_width = 20
    full_name_width = 30
    amount_paid_width = 15
    status_width = 20

    # Define the heading
    heading = "Today's Sales"

    # Print the heading
    centered_heading = ' ' * 50 + heading
    textob.textLine(centered_heading)
    textob.textLine(" ")
    textob.textLine(" ")
    # Print column titles
    column_titles = f"{'Sl. No.':<{serial_width}}{'Order Number':<{order_number_width}}{'Full Name':<{full_name_width}}{'Amount Paid':<{amount_paid_width}}  {'Status':<{status_width}}"
    textob.textLine(column_titles)
    textob.textLine(" ")

    # Print order information with serial numbers
    for index, order in enumerate(orders, start=1):
        # Concatenate all attributes of the order instance into a single string
        if order.address:
            order_info = f"{str(index):<{serial_width}}"
            order_info += f"{str(order.order_number):<{order_number_width}}"
            order_info += f"{order.address.full_name[:full_name_width - 4]:<{full_name_width}}"
            order_info += f"{str(order.payment.amount_paid):<{amount_paid_width}}"
            order_info += f"{order.status[:status_width]:<{status_width}}"
            textob.textLine(order_info)

    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='daily-report.pdf')


def weekly_report_pdf(request):
    buf = io.BytesIO()
    # create canvas
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    # create a text object
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Filter OrderProduct objects for the current week
    orders = Order.objects.filter(created_at__range=[start_of_week, end_of_week]).order_by('-created_at')

    # Define column widths
    serial_width = 10
    order_number_width = 20
    full_name_width = 30
    amount_paid_width = 15
    status_width = 20
    # Define the heading
    heading = "Weekly Sales Report"

    # Print the heading
    centered_heading = ' ' * 50 + heading
    textob.textLine(centered_heading)
    textob.textLine(" ")
    textob.textLine(" ")
    # Print column titles
    column_titles = f"{'No.':<{serial_width}}{'Order Number':<{order_number_width}}{'Full Name':<{full_name_width}}{'Amount Paid':<{amount_paid_width}}  {'Status':<{status_width}}"
    textob.textLine(column_titles)
    textob.textLine(" ")

    # Print order information with serial numbers
    for index, order in enumerate(orders, start=1):
        # Concatenate all attributes of the order instance into a single string
        if order.address:
            order_info = f"{str(index):<{serial_width}}"
            order_info += f"{str(order.order_number):<{order_number_width}}"
            order_info += f"{order.address.full_name[:full_name_width - 4]:<{full_name_width}}"
            order_info += f"{str(order.payment.amount_paid):<{amount_paid_width}}"
            order_info += f"{order.status[:status_width]:<{status_width}}"
            textob.textLine(order_info)

    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='weekly-report.pdf')


def monthly_report_pdf(request):
    buf = io.BytesIO()
    # create canvas
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    # create a text object
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    # Calculate the start and end of the current day
    current_date = datetime.now()
    start_of_month = current_date.replace(month=1, day=1)
    end_of_month = start_of_month.replace(year=start_of_month.year + 1) - timedelta(days=1)

    # Filter OrderProduct objects for the current day
    orders = Order.objects.filter(created_at__range=[start_of_month, end_of_month]).order_by('-created_at')

    # Define column widths
    serial_width = 10
    order_number_width = 20
    full_name_width = 30
    amount_paid_width = 15
    status_width = 20
    # Define the heading
    heading = "Monthly Sales Report"

    # Print the heading
    centered_heading = ' ' * 50 + heading
    textob.textLine(centered_heading)
    textob.textLine(" ")
    textob.textLine(" ")
    # Print column titles
    column_titles = f"{'No.':<{serial_width}}{'Order Number':<{order_number_width}}{'Full Name':<{full_name_width}}{'Amount Paid':<{amount_paid_width}}  {'Status':<{status_width}}"
    textob.textLine(column_titles)
    textob.textLine(" ")

    # Print order information with serial numbers
    for index, order in enumerate(orders, start=1):
        # Concatenate all attributes of the order instance into a single string
        if order.address:
            order_info = f"{str(index):<{serial_width}}"
            order_info += f"{str(order.order_number):<{order_number_width}}"
            order_info += f"{order.address.full_name[:full_name_width - 4]:<{full_name_width}}"
            order_info += f"{str(order.payment.amount_paid):<{amount_paid_width}}"
            order_info += f"{order.status[:status_width]:<{status_width}}"
            textob.textLine(order_info)

    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='monthly-report.pdf')


def yearly_report_pdf(request):
    buf = io.BytesIO()
    # create canvas
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    # create a text object
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    # Calculate the start and end of the current day
    current_date = datetime.now()
    start_of_year = current_date.replace(month=1, day=1)
    end_of_year = start_of_year.replace(year=start_of_year.year + 1) - timedelta(days=1)

    # Filter OrderProduct objects for the current year
    orders = Order.objects.filter(created_at__range=[start_of_year, end_of_year]).order_by('-created_at')

    # Define column widths
    serial_width = 10
    order_number_width = 20
    full_name_width = 30
    amount_paid_width = 15
    status_width = 20
    # Define the heading
    heading = "Yearly Sales Report"

    # Print the heading
    centered_heading = ' ' * 50 + heading
    textob.textLine(centered_heading)
    textob.textLine(" ")
    textob.textLine(" ")
    # Print column titles
    column_titles = f"{'No.':<{serial_width}}{'Order Number':<{order_number_width}}{'Full Name':<{full_name_width}}{'Amount Paid':<{amount_paid_width}}  {'Status':<{status_width}}"
    textob.textLine(column_titles)
    textob.textLine(" ")

    # Print order information with serial numbers
    for index, order in enumerate(orders, start=1):
        # Concatenate all attributes of the order instance into a single string
        if order.address:
            order_info = f"{str(index):<{serial_width}}"
            order_info += f"{str(order.order_number):<{order_number_width}}"
            order_info += f"{order.address.full_name[:full_name_width - 4]:<{full_name_width}}"
            order_info += f"{str(order.payment.amount_paid):<{amount_paid_width}}"
            order_info += f"{order.status[:status_width]:<{status_width}}"
            textob.textLine(order_info)

    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='yearly-report.pdf')
