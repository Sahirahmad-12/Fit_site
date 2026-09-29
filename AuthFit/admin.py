from django.contrib import admin
from .models import Contact, Trainer, MembershipPlan, Attendence, GymNotification
from .models import Enrollment
from django.urls import path
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from django.template.response import TemplateResponse
import json
from datetime import timedelta
from collections import defaultdict
from django.core.cache import cache
from django.db.models import Count, Avg, Max, Min
from django.db.models.functions import ExtractWeekDay, ExtractHour, TruncMonth ,TruncDay
from cloudinary.utils import cloudinary_url
from .models import UserDevice

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'active', 'last_seen')
    list_filter = ('active',)
    search_fields = ('user__username', 'device_name', 'fcm_token')

    
@admin.register(GymNotification)
class GymNotificationAdmin(admin.ModelAdmin):
    list_display = ("icon", "message", "is_active", "order", "created_at")
    list_editable = ("is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("message",)

"""
Add this to your existing admin.py  (AuthFit/admin.py)

This adds a new /admin/attendance/ route with full attendance analytics.
"""

from django.db.models import Count, Avg, Max, Min
from django.db.models.functions import TruncDate, TruncHour, ExtractWeekDay, ExtractHour, TruncMonth
from datetime import timedelta
from collections import defaultdict
import json


def attendance_view(request):
    """
    Admin attendance analytics view.
    Mounted at /admin/attendance/
    """
    if not (request.user.is_staff or request.user.is_superuser):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied.")
    
    cached = cache.get("admin_attendance_data")

    if cached is None:
        now = timezone.now()
        today = timezone.localdate()
        last_30 = now - timedelta(days=30)
        last_7  = now - timedelta(days=7)

        qs = Attendence.objects.all()

        # ── Today's check-ins ──────────────────────────────────────────────
        today_count = qs.filter(date=today).count()
        yesterday_count = qs.filter(date=today - timedelta(days=1)).count()
        today_delta = today_count - yesterday_count

        # ── Day-of-week traffic (1=Sunday … 7=Saturday in Django/MySQL,
        #    or 1=Sunday … 7=Saturday in PostgreSQL — annotate then group)
        day_map = {1:'Sun',2:'Mon',3:'Tue',4:'Wed',5:'Thu',6:'Fri',7:'Sat'}
        dow = (
            qs.filter(date__gte=last_30.date())
            .annotate(dow=ExtractWeekDay('date'))
            .values('dow')
            .annotate(total=Count('id'))
            .order_by('dow')
        )
        # Build ordered Mon-Sun labels
        dow_lookup = {d['dow']: d['total'] for d in dow}
        # Django ExtractWeekDay: 1=Sunday…7=Saturday
        ordered_dow = [2,3,4,5,6,7,1]          # Mon…Sun
        day_labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        day_data   = [dow_lookup.get(d, 0) for d in ordered_dow]

        # ── Hourly traffic (last 30 days) ──────────────────────────────────
        # NOTE: Attendence.timestamp is a TimeField (not DateTimeField).
        # Filter by date field, then extract hour from timestamp TimeField.
        # Gym hours: 5–11 AM (morning) + 4–10 PM (evening), skip midday.
        hourly = (
            qs.filter(date__gte=last_30.date())        # ← use date, not timestamp
            .annotate(hr=ExtractHour('timestamp'))      # timestamp is TimeField — OK
            .values('hr')
            .annotate(total=Count('id'))
            .order_by('hr')
        )
        hour_lookup = {h['hr']: h['total'] for h in hourly}

        # Gym slots: 5,6,7,8,9,10,11  then  16,17,18,19,20,21,22
        hour_range  = list(range(5, 12)) + list(range(16, 23))

        def _fmt(h):
            hh  = h if h <= 12 else h - 12
            suf = 'am' if h < 12 else 'pm'
            return f"{hh}{suf}" if h != 12 else '12p'

        hour_labels = [_fmt(h) for h in hour_range]
        hour_data   = [hour_lookup.get(h, 0) for h in hour_range]

        # Peak hour (across all slots)
        peak_hr = max(hour_lookup, key=hour_lookup.get) if hour_lookup else 18
        next_hr = peak_hr + 1
        peak_hr_label = (
            f"{peak_hr if peak_hr<=12 else peak_hr-12}"
            f"{'am' if peak_hr<12 else 'pm'}"
            f" – "
            f"{next_hr if next_hr<=12 else next_hr-12}"
            f"{'am' if next_hr<12 else 'pm'}"
        )

        # Busiest day label
        best_dow_idx = day_data.index(max(day_data)) if day_data else 0
        busiest_day  = day_labels[best_dow_idx]

        # ── Heatmap: day-of-week × hour (last 30 days) ────────────────────
        # timestamp is a TimeField → filter on date, extract hour from timestamp
        heatmap_raw = (
            qs.filter(date__gte=last_30.date())
            .annotate(dow=ExtractWeekDay('date'), hr=ExtractHour('timestamp'))
            .values('dow', 'hr')
            .annotate(total=Count('id'))
        )
        hm = defaultdict(lambda: defaultdict(int))
        for row in heatmap_raw:
            hm[row['dow']][row['hr']] = row['total']

        # Same gym slots: 5–11 AM + 4–10 PM
        hm_hour_range = list(range(5, 12)) + list(range(16, 23))
        heatmap = {}
        for label, db_dow in zip(day_labels, ordered_dow):
            heatmap[label] = [hm[db_dow].get(h, 0) for h in hm_hour_range]

        # ── Monthly trend (last 6 months) ─────────────────────────────────
        six_months_ago = now - timedelta(days=180)
        monthly = (
            qs.filter(date__gte=six_months_ago.date())
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total=Count('id'))
            .order_by('month')
        )
        month_labels = [m['month'].strftime("%b %Y") for m in monthly if m['month']]
        month_data   = [m['total'] for m in monthly]

        # ── At-risk / absentee members ────────────────────────────────────
        # Members who have attended at least once but not in the last N days
        cutoff_danger  = today - timedelta(days=14)
        cutoff_warning = today - timedelta(days=7)

        all_users_with_attendance = (
            Attendence.objects
            .values('user_id')
            .annotate(last_date=Max('date'))
        )

        at_risk = []
        for row in all_users_with_attendance:
            days_absent = (today - row['last_date']).days
            if days_absent >= 5:
                try:
                    enroll = Enrollment.objects.select_related('user').get(user_id=row['user_id'])
                    status = 'danger' if days_absent >= 14 else 'warning' if days_absent >= 7 else 'notice'
                    at_risk.append({
                        'name': enroll.fullname,
                        'uid':  enroll.unique_id,
                        'last': row['last_date'].strftime("%b %d"),
                        'days': days_absent,
                        'status': status,
                    })
                except Enrollment.DoesNotExist:
                    pass

        at_risk.sort(key=lambda x: -x['days'])
        at_risk = at_risk[:10]          # top 10

        # ── Quick retention numbers ────────────────────────────────────────
        total_enrolled    = Enrollment.objects.count()
        active_this_month = qs.filter(date__year=today.year, date__month=today.month).values('user').distinct().count()
        retention_pct     = round(active_this_month / total_enrolled * 100, 1) if total_enrolled else 0

        # ── Avg daily visits this month ────────────────────────────────────
        days_elapsed = today.day
        month_total  = qs.filter(date__year=today.year, date__month=today.month).count()
        avg_daily    = round(month_total / days_elapsed, 1) if days_elapsed else 0

        cached = {
            "today_count":    today_count,
            "today_delta":    today_delta,
            "peak_hr_label":  peak_hr_label,
            "busiest_day":    busiest_day,
            "at_risk_count":  len([m for m in at_risk if m['status'] == 'danger']),

            "day_labels":    day_labels,
            "day_data":      day_data,
            "hour_labels":   hour_labels,
            "hour_data":     hour_data,
            "month_labels":  month_labels,
            "month_data":    month_data,

            "heatmap":       heatmap,
            "hour_range":    hour_range,

            "at_risk":       at_risk,

            "total_enrolled":    total_enrolled,
            "active_this_month": active_this_month,
            "retention_pct":     retention_pct,
            "avg_daily":         avg_daily,
        }

        cache.set("admin_attendance_data", cached, timeout=120)   # 2-min cache

    context = dict(
        admin.site.each_context(request),

        today_count   = cached["today_count"],
        today_delta   = cached["today_delta"],
        peak_hr_label = cached["peak_hr_label"],
        busiest_day   = cached["busiest_day"],
        at_risk_count = cached["at_risk_count"],

        day_labels  = json.dumps(cached["day_labels"]),
        day_data    = json.dumps(cached["day_data"]),
        hour_labels = json.dumps(cached["hour_labels"]),
        hour_data   = json.dumps(cached["hour_data"]),
        month_labels= json.dumps(cached["month_labels"]),
        month_data  = json.dumps(cached["month_data"]),

        heatmap_json    = json.dumps(cached["heatmap"]),
        hour_range_json = json.dumps(cached["hour_range"]),

        at_risk      = cached["at_risk"],

        total_enrolled    = cached["total_enrolled"],
        active_this_month = cached["active_this_month"],
        retention_pct     = cached["retention_pct"],
        avg_daily         = cached["avg_daily"],
    )

    return TemplateResponse(request, "admin/attendance_analysis.html", context)

def revenue_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access denied.")

    data = cache.get("admin_revenue_data")

    if data is None:

        qs = Enrollment.objects.all()

        # 📊 Monthly Revenue
        monthly = (
            qs.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('Amount'))
            .order_by('month')
        )

        # 📅 Daily Revenue
        last_7_days = timezone.now() - timezone.timedelta(days=7)

        daily = (
            qs.filter(created_at__gte=last_7_days)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('Amount'))
            .order_by('day')
        )

        # 📈 Member Growth
        members = (
            Enrollment.objects.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # 💳 Payment Analytics
        payments = (
            Enrollment.objects
            .exclude(paymentStatus__isnull=True)
            .values('paymentStatus')
            .annotate(count=Count('id'))
        )

        # 💸 Pending Dues
        pending_qs = Enrollment.objects.filter(
            pendingAmount__gt=0,
            paymentStatus="Pending"
        )
        pending_count  = pending_qs.count()
        pending_amount = pending_qs.aggregate(total=Sum('pendingAmount'))['total'] or 0

        # ✅ STORE CLEAN DATA ONLY
        data = {
            "monthly_labels": [x['month'].strftime("%b %Y") for x in monthly if x['month']],
            "monthly_data":   [float(x['total'] or 0) for x in monthly],

            "daily_labels": [x['day'].strftime("%d %b") for x in daily if x['day']],
            "daily_data":   [float(x['total'] or 0) for x in daily],

            "member_labels": [x['month'].strftime("%b %Y") for x in members if x['month']],
            "member_data":   [x['count'] for x in members],

            "payment_labels": [x['paymentStatus'] for x in payments],
            "payment_data":   [x['count'] for x in payments],

            "total_revenue":  sum([x['total'] or 0 for x in monthly]),
            "today_revenue":  sum([x['total'] or 0 for x in daily]),
            "total_members":  Enrollment.objects.count(),

            "pending_count":  pending_count,
            "pending_amount": float(pending_amount),
        }

        cache.set("admin_revenue_data", data, timeout=60)

    # ✅ BUILD CONTEXT (DO NOT CACHE THIS)
    context = dict(
        admin.site.each_context(request),

        monthly_labels=json.dumps(data["monthly_labels"]),
        monthly_data=json.dumps(data["monthly_data"]),

        daily_labels=json.dumps(data["daily_labels"]),
        daily_data=json.dumps(data["daily_data"]),

        member_labels=json.dumps(data["member_labels"]),
        member_data=json.dumps(data["member_data"]),

        payment_labels=json.dumps(data["payment_labels"]),
        payment_data=json.dumps(data["payment_data"]),

        total_revenue=data["total_revenue"],
        today_revenue=data["today_revenue"],
        total_members=data["total_members"],

        pending_count=data["pending_count"],
        pending_amount=data["pending_amount"],
    )

    return TemplateResponse(request, "admin/revenue.html", context)


original_get_urls = admin.site.get_urls


def custom_get_urls():
    urls = original_get_urls()
    custom_urls = [
        path('revenue/', admin.site.admin_view(revenue_view)),
        path('attendance/', admin.site.admin_view(attendance_view)),
    ]
    return custom_urls + urls


admin.site.get_urls = custom_get_urls

# Register your models here.
admin.site.register(Contact)
admin.site.register(Trainer)
admin.site.register(MembershipPlan)


@admin.register(Attendence)
class AttendenceAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'member_name', 'pending_amount',
                    'remaining_day', 'date', 'timestamp')
    search_fields = ('user__enrollment__fullname',
                     'user__enrollment__unique_id')
    list_filter = ('date',)

    def member_id(self, obj):
        return obj.user.enrollment.unique_id
    member_id.short_description = "MEMBER ID"

    def member_name(self, obj):
        return obj.user.enrollment.fullname
    member_name.short_description = "NAME"

    def pending_amount(self, obj):          
        return obj.user.enrollment.pendingAmount   
    pending_amount.short_description = "PENDING Rs"

    def remaining_day(self, obj):
        return obj.user.enrollment.DueDate
    remaining_day.short_description = "REMAINING DAYS"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "unique_id",
        "fullname",
        "phone",
        "selectPlan",
        "pendingAmount",
        "paymentStatus",
        "days_remaining",
        "face_preview",
    )

    search_fields = ("unique_id", "fullname", "phone", "email")

    list_filter = ("paymentStatus", "selectPlan", "trainer", "gender")

    readonly_fields = ("face_preview",)  # ✅ show in detail page

    # ✅ IMAGE PREVIEW FUNCTION
    def face_preview(self, obj):
        if not obj.face_image:
            return "No Image"
        try:
            url, _ = cloudinary_url(
                obj.face_image.public_id,
                width=50, height=50,
                crop="fill", gravity="face",
                secure=True,   # ← forces https://
            )
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover;" />',
                url
            )
        except Exception:
            return "—"
