from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import models, forms

# Create your views here.
@require_POST
def coupon_apply(request):
    now = timezone.now()
    form = forms.CouponApplyForm(require.POST)
    if form.is_valid():
        code = form.cleaned_data['code']
        try:
            coupon = models.Coupon.objects.get(code__iexact=code,
                                               valid_from__lte=now,
                                               valid_to__gte=now,
                                               active=True)
            request.session['coupon_id'] = coupon.id
        except models.Coupon.DoesNotExist:
            request.session['coupon_id'] = None
    return redirect('cart:cart_detail')