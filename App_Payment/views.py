from django.shortcuts import redirect, render, HttpResponseRedirect
from django.urls import reverse
from App_Order.models import Cart, Order
from App_Payment.forms import BillingAdress
from App_Payment.forms import BillingForm
from django.contrib import messages

from django.contrib.auth.decorators import login_required

# for Payment
import requests
# import sslcommerz_lib
# print(dir(sslcommerz_lib))
from sslcommerz_lib import SSLCOMMERZ
from decimal import Decimal
import socket
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
def checkout(request):
    saved_address = BillingAdress.objects.get_or_create(user=request.user)
    saved_address = saved_address[0]
    form = BillingForm(instance=saved_address)
    if request.method =="POST":
        form = BillingForm(request.POST, instance=saved_address)
        if form.is_valid():
            form.save()
            form = BillingForm(instance=saved_address)
            messages.success(request, f"Shipping Address Saved!!")
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    #print(order_qs)
    order_items = order_qs[0].orderitems.all()
    #print(order_items)
    order_total = order_qs[0].get_totals()
    #print(order_total)
    return render(request, 'App_Payment/checkout.html', context={'form':form, 'order_items':order_items, 'order_total':order_total, 'saved_address':saved_address})
@login_required
def payment(request):
    saved_address = BillingAdress.objects.get_or_create(user=request.user)
    if not saved_address[0].is_fully_filled():
        messages.info(request, f"Please add shippping adress!")
        return redirect("App_Payment:checkout")
    
    if not request.user.profile.is_fully_filled():
        messages.info(request, f"please complete profile details")
        return redirect("App_Login:profile")
    
    store_id = 'bmtra667e8fc5caf13'
    store_pass = 'bmtra667e8fc5caf13@ssl'
    settings = {'store_id': store_id, 'store_pass': store_pass, 'issandbox': True}
    sslcz = SSLCOMMERZ(settings)

    status_url = request.build_absolute_uri(reverse("App_Payment:complete"))

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    order_items = order_qs[0].orderitems.all()
    order_items_count = order_qs[0].orderitems.count()
    order_total = order_qs[0].get_totals()

    post_body = {
        'total_amount': Decimal(order_total),
        'currency': 'BDT',
        'tran_id': "12345",  # You may want to generate a unique transaction ID
        'success_url': status_url,
        'fail_url': status_url,
        'cancel_url': status_url,
        'emi_option': 0,
        'cus_name': request.user.profile.full_name,
        'cus_email': request.user.email,
        'cus_phone': request.user.profile.phone,
        'cus_add1': request.user.profile.adress_1,
        'cus_city': request.user.profile.city,
        'cus_country': request.user.profile.country,
        'shipping_method': 'Courier',
        'num_of_item': order_items_count,
        'product_name': str(order_items),
        'product_category': 'Mixed',
        'product_profile': 'general',
    }

    try:
        response = sslcz.createSession(post_body)
        logger.info(f"SSLCommerz API response: {response}")

        if 'GatewayPageURL' in response:
            return redirect(response['GatewayPageURL'])
        else:
            messages.error(request, "Unable to redirect to payment gateway. Please try again later.")
            return redirect("App_Shop:home")  # Redirect to home or another page on failure
    except Exception as e:
        logger.error(f"SSLCommerz session is under development: {str(e)}")
        messages.error(request, "please send your payment at bkash(01721516460). processing your payment.")
        return redirect("App_Shop:home") 

@csrf_exempt
def complete(request):
    if request.method == 'POST' or request.method == 'post':
        payment_data = request.POST
        status = payment_data['status']

        if status == 'VALID':
            val_id = payment_data['val_id']
            tran_id = payment_data['tran_id']
            messages.success(request, "Your Payment Completed Successfully! Page will be redirected!")
            return HttpResponseRedirect(reverse("App_Payment:purchase", kwargs={'val_id': val_id, 'tran_id': tran_id},))
        elif status == 'FAILED':
            messages.warning(request, "Your Payment Failed! Please Try Again! Page will be redirected!")

    return render(request, "App_Payment/complete.html", context={})

@login_required
def purchase(request, val_id, tran_id):
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    order = order_qs[0]
    orderId = tran_id
    order.ordered = True
    order.orderId = orderId
    order.paymentId = val_id
    order.save()
    cart_items = Cart.objects.filter(user=request.user, purchased=False)
    for item in cart_items:
        item.purchased = True
        item.save()
    return HttpResponseRedirect(reverse("App_Shop:home"))

@login_required
def order_view(request):
    try:
        orders = Order.objects.filter(user=request.user, ordered=True)
        context = {"orders": orders}
    except:
        messages.warning(request, "You do not have an active order")
        return redirect("App_Shop:home")
    return render(request, "App_Payment/order.html", context)