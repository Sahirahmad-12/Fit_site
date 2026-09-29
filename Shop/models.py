from decimal import Decimal
from functools import cached_property

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from cloudinary.models import CloudinaryField


# ── constants ─────────────────────────────────────────────────────────────────

STOCK_BUFFER = 2  # Reserve this many units — never exposed to users


class Product(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField()
    base_price  = models.DecimalField(max_digits=10, decimal_places=2)
    image       = CloudinaryField('image', blank=True, null=True)
    discount    = models.IntegerField(default=0)
    active      = models.BooleanField(default=True)

    # ── computed prices ──────────────────────────────────────────────────────
    @cached_property
    def discounted_price(self) -> Decimal:
        return self.base_price * (1 - Decimal(self.discount) / 100)

    @cached_property
    def discount_amount(self) -> Decimal:
        return self.base_price - self.discounted_price

    # ── stock helpers ────────────────────────────────────────────────────────
    def get_total_stock(self) -> int:
        """Raw stock — sum of all flavors. Use for internal/admin purposes."""
        result = self.flavors.aggregate(total=Sum('stock'))['total']
        return result or 0

    def get_available_stock(self) -> int:
        """
        User-facing stock: raw stock minus the buffer.
        Always ≥ 0. This is the ceiling for order quantities.
        """
        return max(0, self.get_total_stock() - STOCK_BUFFER)

    @property
    def in_stock(self) -> bool:
        """True only if user-facing stock > 0."""
        if 'flavors' in self.__dict__.get('_prefetched_objects_cache', {}):
            return any(f.available_stock > 0 for f in self.flavors.all())
        return self.flavors.filter(stock__gt=STOCK_BUFFER).exists()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ProductFlavor(models.Model):
    product          = models.ForeignKey(Product, related_name='flavors', on_delete=models.CASCADE)
    name             = models.CharField(max_length=100)
    stock            = models.PositiveIntegerField(default=0)
    price_adjustment = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)


    @cached_property
    def final_price(self) -> Decimal:
        """Product's discounted price + this flavor's price adjustment."""
        return self.product.discounted_price + self.price_adjustment

    @property
    def available_stock(self) -> int:
        """
        User-facing stock for this flavor: real stock minus the buffer.
        This is the ceiling enforced on order quantities.
        """
        return max(0, self.stock - STOCK_BUFFER)

    @property
    def in_stock(self) -> bool:
        return self.available_stock > 0

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    class Meta:
        ordering = ['name']


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'Pending',   'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'   # Admin sets this: item has arrived at gym
        DELIVERED = 'Delivered', 'Delivered'   # Admin sets this: member has collected it
        CANCELLED = 'Cancelled', 'Cancelled'

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    product     = models.ForeignKey(Product, on_delete=models.CASCADE)
    flavor      = models.ForeignKey(
        ProductFlavor, null=True, blank=True, on_delete=models.SET_NULL
    )
    quantity    = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status      = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        db_index=True,   # speeds up filtering by status in admin / my_orders
    )
    ordered_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # ── helpers used by templates ────────────────────────────────────────────
    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_confirmed(self) -> bool:
        return self.status == self.Status.CONFIRMED

    @property
    def is_delivered(self) -> bool:
        return self.status == self.Status.DELIVERED

    @property
    def is_cancelled(self) -> bool:
        return self.status == self.Status.CANCELLED

    def __str__(self):
        return f"Order#{self.pk} — {self.user.username} × {self.product.name}"

    class Meta:
        ordering = ['-ordered_at']


class StaffDevice(models.Model):
    """
    Stores the FCM push token for each device belonging to a staff/owner user.
    One user can have multiple devices (phone + tablet etc.).
    """
    fcm_token       = models.TextField(unique=True)
    device_name     = models.CharField(max_length=120, blank=True)  # e.g. "Galaxy S24"
    last_seen       = models.DateTimeField(auto_now=True)
    active          = models.BooleanField(default=True)
 
    def __str__(self):
        return f"{self.device_name} ({'Active' if self.active else 'Inactive'})"
 
    class Meta:
        ordering = ['-last_seen']
        verbose_name        = 'Staff Device'
        verbose_name_plural = 'Staff Devices'
 