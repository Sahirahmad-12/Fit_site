from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from cloudinary.utils import cloudinary_url
from django.db.models import Count, Q, Sum
from AuthFit.models import Enrollment
from .models import STOCK_BUFFER, Order, Product, ProductFlavor
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required


# ── shared helpers ─────────────────────────────────────────────────────────────

def _get_active_product(product_id):
    return get_object_or_404(
        Product.objects.prefetch_related('flavors'),
        id=product_id, active=True,
    )


def _resolve_flavor(request, product):
    flavor_id = request.POST.get('flavor')
    if not flavor_id or flavor_id == 'standard':
        return None, True
    try:
        return product.flavors.get(id=int(flavor_id)), True
    except (ProductFlavor.DoesNotExist, ValueError):
        messages.error(request, "Invalid flavour selected.")
        return None, False


def _soft_available(flavor, product):
    return flavor.available_stock if flavor else product.get_available_stock()


def _validate_soft_stock(request, flavor, product, quantity):
    available = _soft_available(flavor, product)
    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return False
    if quantity > available:
        messages.error(
            request,
            f"Only {available} unit(s) available." if available > 0
            else "This item is currently out of stock."
        )
        return False
    return True


def _get_enrollment(user):
    """Return Enrollment for the user, cached for 5 min."""
    enrollment = cache.get(f"enrollment_{user.id}")
    if enrollment is None:
        enrollment = Enrollment.objects.filter(user=user).first()
        cache.set(f"enrollment_{user.id}", enrollment, timeout=300)
    return enrollment


def _get_profile_image(user, enrollment):
    if not (enrollment and enrollment.face_image):
        return None
    image_url = cache.get(f"profile_image_{user.id}")
    if image_url is None:
        try:
            public_id = (
                enrollment.face_image.public_id
                if hasattr(enrollment.face_image, "public_id")
                else str(enrollment.face_image)
            )
            image_url, _ = cloudinary_url(public_id, width=130, height=130, crop="fill")
            cache.set(f"profile_image_{user.id}", image_url, timeout=300)
        except Exception:
            image_url = None
    return image_url


# ═══════════════════════════════════════════════════════════════════════════════
#  PRODUCT VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def product_list(request):
    products = Product.objects.filter(active=True).prefetch_related('flavors')
    return render(request, 'shop/product_list.html', {'products': products})


@login_required
def product_detail(request, product_id):
    product = _get_active_product(product_id)
    return render(request, 'shop/product_detail.html', {'product': product})


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIRM ORDER  (GET — show summary before placing)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def confirm_order(request, product_id):
    product = _get_active_product(product_id)
    if request.method != 'POST':
        return redirect('product_detail', product_id=product_id)

    flavor, ok = _resolve_flavor(request, product)
    if not ok:
        return redirect('product_detail', product_id=product_id)

    quantity = int(request.POST.get('quantity', 1))
    if not _validate_soft_stock(request, flavor, product, quantity):
        return redirect('product_detail', product_id=product_id)

    unit_price  = flavor.final_price if flavor else product.discounted_price
    total_price = unit_price * Decimal(quantity)

    enrollment  = _get_enrollment(request.user)
    image_url   = _get_profile_image(request.user, enrollment)

    return render(request, 'shop/confirm_order.html', {
        'product':     product,
        'flavor':      flavor,
        'quantity':    quantity,
        'unit_price':  unit_price,
        'total_price': total_price,
        'enrollment':  enrollment,
        'image_url':   image_url,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  PLACE ORDER  (POST — atomic, decrements stock)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@transaction.atomic
def place_order(request):
    if request.method != 'POST':
        return redirect('product_list')
 
    product_id = request.POST.get('product_id')
    product    = _get_active_product(product_id)
    quantity   = int(request.POST.get('quantity', 1))
 
    flavor, ok = _resolve_flavor(request, product)
    if not ok:
        return redirect('product_detail', product_id=product_id)
 
    # Lock rows + hard stock check
    if flavor:
        flavor     = ProductFlavor.objects.select_for_update().get(id=flavor.id)
        real_stock = flavor.stock
    else:
        flavors    = list(ProductFlavor.objects.select_for_update().filter(product=product))
        real_stock = sum(f.stock for f in flavors)
 
    if quantity < 1 or quantity > real_stock:
        messages.error(request, f"Sorry, only {real_stock} unit(s) left.")
        return redirect('product_detail', product_id=product_id)
 
    unit_price  = flavor.final_price if flavor else product.discounted_price
    total_price = unit_price * Decimal(quantity)
 
    order = Order.objects.create(
        user=request.user,
        product=product,
        flavor=flavor,
        quantity=quantity,
        total_price=total_price,
        status=Order.Status.PENDING,
    )
 
    # Decrement stock immediately on order placement
    if flavor:
        ProductFlavor.objects.filter(id=flavor.id).update(stock=flavor.stock - quantity)
 
    # ── Push notification to all staff devices ────────────────────────────────
    # Runs after the transaction commits so the order is visible in DB
    # Uses transaction.on_commit to avoid notifying before the row is saved
    from .notifications import notify_staff_new_order
    transaction.on_commit(lambda: notify_staff_new_order(order))
    # ─────────────────────────────────────────────────────────────────────────
 
    enrollment = _get_enrollment(request.user)
    image_url  = _get_profile_image(request.user, enrollment)
 
    return render(request, 'shop/order_success.html', {
        'order':      order,
        'enrollment': enrollment,
        'image_url':  image_url,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  MY ORDERS  (list + track)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def my_orders(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .select_related('product', 'flavor')
        .order_by('-ordered_at')
    )
    enrollment = _get_enrollment(request.user)
    image_url  = _get_profile_image(request.user, enrollment)

    return render(request, 'shop/my_orders.html', {
        'orders':     orders,
        'enrollment': enrollment,
        'image_url':  image_url,
    })


def _status_counts(qs):
    counts = qs.values('status').annotate(n=Count('id'))
    return {row['status']: row['n'] for row in counts}


@staff_member_required
def order_dashboard(request):
    """
    Lists all orders, filterable by status tab.
    GET ?status=Pending|Confirmed|Delivered|Cancelled  (default: Pending)
    GET ?q=<search>  searches order id, username, product name
    """
    status_filter = request.GET.get('status', 'Pending')
    search        = request.GET.get('q', '').strip()
 
    qs = (
        Order.objects
        .select_related('user', 'product', 'flavor')
        .order_by('-ordered_at')
    )
 
    if search:
        qs = qs.filter(
            Q(id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(product__name__icontains=search)
        )
 
    all_counts = _status_counts(Order.objects.all())
 
    # Apply status tab filter (skip when searching — show all results)
    if not search:
        qs = qs.filter(status=status_filter)
 
    # Revenue stat (delivered orders only)
    revenue = Order.objects.filter(
        status=Order.Status.DELIVERED
    ).aggregate(total=Sum('total_price'))['total'] or 0
 
    return render(request, 'shop/admin_orders.html', {
        'orders':        qs,
        'status_filter': status_filter if not search else '',
        'search':        search,
        'all_counts':    all_counts,
        'revenue':       revenue,
        'Status':        Order.Status,
        # Next-action map: what button to show per current status
        'next_action': {
            Order.Status.PENDING:   ('Confirm — Item at Gym', Order.Status.CONFIRMED, 'confirm'),
            Order.Status.CONFIRMED: ('Mark Collected',        Order.Status.DELIVERED, 'deliver'),
        },
    })
 
 
@staff_member_required
@require_POST
def order_update(request, order_id):
    """
    Advances an order to the next status.
    POST body: action = confirm | deliver | cancel
    Returns JSON if AJAX (X-Requested-With: XMLHttpRequest), else redirect.
    """
    order  = get_object_or_404(Order, id=order_id)
    action = request.POST.get('action')
 
    TRANSITIONS = {
        'confirm': (Order.Status.PENDING,   Order.Status.CONFIRMED),
        'deliver': (Order.Status.CONFIRMED, Order.Status.DELIVERED),
        'cancel':  (None,                   Order.Status.CANCELLED),   # None = any state
    }
 
    if action not in TRANSITIONS:
        msg = 'Invalid action.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('admin_orders')
 
    expected_from, new_status = TRANSITIONS[action]
 
    # Guard: cancel is allowed from Pending or Confirmed only
    if action == 'cancel' and order.status not in (Order.Status.PENDING, Order.Status.CONFIRMED):
        msg = f'Cannot cancel an order with status "{order.status}".'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('admin_orders')
 
    if expected_from and order.status != expected_from:
        msg = f'Expected status "{expected_from}", got "{order.status}".'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('admin_orders')
 
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])
 
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'new_status': new_status})
 
    messages.success(request, f'Order #{order.id} updated to "{new_status}".')
    return redirect(request.META.get('HTTP_REFERER', 'admin_orders'))