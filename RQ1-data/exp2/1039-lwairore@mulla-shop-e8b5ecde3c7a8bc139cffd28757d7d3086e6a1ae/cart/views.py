from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from shop import models as shop_models
from . import cart as item_cart
from . import forms

# Create your views here.
@require_POST
def cart_add(request, product_id):
    cart = item_cart.Cart(request)
    product = get_object_or_404(shop_models.Product, id=product_id)
    form = forms.CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product,
                 quantity=cd['quantity'], update_quantity=cd['update'])
    return redirect('cart:cart_detail')


def cart_remove(request, product_id):
    cart = item_cart.Cart(request)
    product = get_object_or_404(shop_models.Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')


def cart_detail(require):
    cart = item_cart.Cart(request)
    return render(request, 'cart/detail.html', {'cart', cart})