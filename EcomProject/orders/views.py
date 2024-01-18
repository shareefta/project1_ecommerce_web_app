from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Order, OrderProduct, Payment
from carts.models import CartItem
from  store.models import Product
import datetime
from django.contrib import messages
import uuid
from accounts.models import Address
from accounts.forms import AddressForm

# Create your views here.

def add_billing_address(request):
    return render(request, 'orders/add-address-billing.html')

def place_order(request, quantity=0, total=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()

    if cart_count <= 0:
        return redirect('store')

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total)/100
    grand_total = total+tax


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
        yr = int(datetime.date.today().strftime('%Y'))
        mt = int(datetime.date.today().strftime('%m'))
        dt = int(datetime.date.today().strftime('%d'))
        d = datetime.date(yr,mt,dt)
        current_date = d.strftime("%Y%m%d")
        order_number = current_date + str(data.id)
        data.order_number = order_number
        data.save()

        order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

        context = {
            'order_address' : order_address,
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total
        }

        return render(request, 'orders/place-order.html', context)

    else:
        return HttpResponse('Error!')

def make_payments(request, order_id):
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
                    user = current_user,
                    payment_id = payment_id,
                    amount_paid = order.order_total,
                    status = 'Completed'
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

                    #Reduce the stock of product sold:
                    product = Product.objects.get(id=item.product_id)
                    product.stock -= item.quantity
                    product.save()

                #Clear Cart:
                CartItem.objects.filter(user=request.user).delete()

                messages.success(request, 'Order placed successfully.')
                return redirect('orders:order_confirmation', order_id=order.id)
            else:
                # Handle other payment methods or show an error message
                messages.error(request, 'Select a valid payment method.')
        else:
            # Handle the case where the order does not exist or is not in a suitable state for payment
            messages.error(request, 'Invalid order or order not in a valid state for payment.')
            return redirect('home')
    else:
        return render(request, 'orders/place-order.html', {'order': order})


def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order-confirmation.html', {'order': order})

