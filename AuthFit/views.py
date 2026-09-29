import secrets
import os
import json
from datetime import date, timedelta
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_log, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from cloudinary.utils import cloudinary_url
from django.utils.http import url_has_allowed_host_and_scheme
from AuthFit.models import (
    Contact, Enrollment, MembershipPlan, Trainer,
    Attendence as Attendence_model, GymNotification
)
from AuthFit.rate_limit import check_login_attempt, reset_attempt, record_failed_attempt
from .attendance import mark_attendance
from .forms import UserLogin
from urllib.parse import urlparse, quote
import cloudinary.uploader
from PIL import Image
import io
from django.core.paginator import Paginator
import logging
from django.db import transaction
from Shop.notifications import notify_staff_new_enrollment
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_EXTENSIONS  = {'.jpg', '.jpeg', '.png', '.webp'}


# ==============================
# INTERNAL API KEY
# ==============================
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")


def _check_internal_key(request):
    provided = request.headers.get("X-Internal-Key", "")
    if not INTERNAL_API_KEY or not provided:
        return False
    return secrets.compare_digest(provided, INTERNAL_API_KEY)


# ==============================
# STAFF CHECK
# ==============================
def is_staff(user):
    return user.is_staff or user.is_superuser


# ==============================
# GET CLIENT IP
# ==============================
def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        ip = forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ==============================
# SAVE EMBEDDINGS BATCH
# ==============================
@csrf_exempt
def save_embeddings_batch(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        if not _check_internal_key(request):
            logger.warning("Invalid internal API key")
            return JsonResponse({"error": "Unauthorized"}, status=403)

        data = json.loads(request.body)
        unique_id = data.get("unique_id")
        embeddings = data.get("embeddings", [])

        if not unique_id:
            return JsonResponse({"error": "Missing unique_id"}, status=400)
        if not embeddings:
            return JsonResponse({"error": "Missing embeddings"}, status=400)

        enrollment = Enrollment.objects.get(unique_id=unique_id)
        face_embeddings = enrollment.face_embeddings or []
        MAX_EMB = 7

        for emb in embeddings:
            if len(face_embeddings) >= MAX_EMB:
                face_embeddings.pop(0)
            face_embeddings.append(emb)

        enrollment.face_embeddings = face_embeddings
        enrollment.face_enrolled = True
        enrollment.save(update_fields=["face_embeddings", "face_enrolled"])

        logger.info(
            "Embeddings updated for enrollment_id=%s user_id=%s",
            enrollment.id, enrollment.user_id
        )

        return JsonResponse({
            "status": "success",
            "total_embeddings": len(face_embeddings)
        })

    except Enrollment.DoesNotExist:
        return JsonResponse({"error": "Enrollment not found"}, status=404)
    except Exception:
        logger.exception("Unexpected error in save_embeddings_batch")
        return JsonResponse({"error": "An internal error occurred."}, status=500)


# ==============================
# SIGNUP PAGE
# ==============================
def signupPage(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == "POST":
        form = UserLogin(request.POST)
        if form.is_valid():
            user = form.save()
            auth_log(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('/')
    else:
        form = UserLogin()

    return render(request, 'registration/signup.html', {'form': form})


# ==============================
# LOGIN PAGE
# ==============================
def loginPage(request):
    if request.user.is_authenticated:
        return redirect('/')

    next_url = request.GET.get('next') or request.POST.get('next', '/')

    if request.method == "POST":
        ip = get_client_ip(request)
        phone = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not check_login_attempt(ip, phone):
            messages.error(request, "Too many failed login attempts. Please try again later.")
            return redirect(f'/login/?next={next_url}')

        user = authenticate(request, username=phone, password=password)

        if user is not None:
            reset_attempt(ip, phone)
            auth_log(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect(_safe_next(next_url, request))
        else:
            record_failed_attempt(ip, phone)
            messages.error(request, "Incorrect phone number or password.")
            return redirect(f'/login/?next={next_url}')

    return render(request, 'registration/login.html', {'next': next_url})


def _safe_next(next_url: str, request) -> str:
    if not next_url:
        return '/'
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=not settings.DEBUG,
    ):
        return next_url
    return '/'


# ==============================
# MARK ATTENDANCE API
# ==============================
@csrf_exempt
def mark_attendance_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        if not _check_internal_key(request):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        data = json.loads(request.body)
        unique_id = data.get("unique_id")
        if not unique_id:
            return JsonResponse({"error": "Missing unique_id"}, status=400)

        result = mark_attendance(unique_id)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception:
        logger.exception("Unexpected error in mark_attendance_api")
        return JsonResponse({"error": "An internal error occurred."}, status=500)


# ==============================
# GET USERS (face embeddings)
# ==============================
@csrf_exempt
def get_users(request):
    if not _check_internal_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = cache.get("face_users")
    if data is None:
        enrollments = Enrollment.objects.filter(face_embeddings__isnull=False)
        data = [
            {
                "unique_id":  u.unique_id,
                "name":       u.fullname,
                "embeddings": u.face_embeddings,
            }
            for u in enrollments
        ]
        cache.set("face_users", data, timeout=300)

    return JsonResponse(data, safe=False)

# ==============================
# RUN EXPIRY CHECK (cron trigger)
# ==============================
@csrf_exempt
def run_expiry_check(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        if not _check_internal_key(request):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        from AuthFit.notifications import send_expiry_reminders
        count = send_expiry_reminders()
        return JsonResponse({"ok": True, "sent": count})
    except Exception:
        logger.exception("Unexpected error in run_expiry_check")
        return JsonResponse({"error": "An internal error occurred."}, status=500)

# ==============================
# UPLOAD FACE IMAGE
# ==============================
@csrf_exempt
def upload_face_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        if not _check_internal_key(request):
            logger.warning("Invalid internal API key")
            return JsonResponse({"error": "Unauthorized"}, status=403)

        unique_id = request.POST.get("unique_id")
        face_image = request.FILES.get("face_image")

        if not unique_id:
            return JsonResponse({"error": "Missing unique_id"}, status=400)
        if not face_image:
            return JsonResponse({"error": "Missing face_image"}, status=400)

        enrollment = Enrollment.objects.get(unique_id=unique_id)
        enrollment.face_image = face_image
        enrollment.save(update_fields=["face_image"])

        cache.delete(f"profile_image_{enrollment.user.id}")
        cache.delete(f"enrollment_{enrollment.user.id}")

        logger.info(
            "Face image updated for enrollment_id=%s user_id=%s",
            enrollment.id, enrollment.user_id
        )

        return JsonResponse({
            "status": "success",
            "image_url": enrollment.face_image.url
        })

    except Enrollment.DoesNotExist:
        return JsonResponse({"error": "Enrollment not found"}, status=404)
    except Exception:
        logger.exception("Unexpected error in upload_face_image")
        return JsonResponse({"error": "An internal error occurred."}, status=500)


@login_required
def upload_profile_pic(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    enrollment = Enrollment.objects.filter(user=request.user).first()
    if not enrollment:
        messages.error(request, "You are not enrolled yet.")
        return redirect('/profile/')

    pic = request.FILES.get("profile_pic")
    if not pic:
        messages.error(request, "No image selected.")
        return redirect('/profile/')

    # ── 1. Delete OLD image from Cloudinary ──────────────────────────────
    # face_image may be a CloudinaryField resource OR a plain public_id string
    if enrollment.face_image:
        try:
            # CloudinaryField exposes .public_id; plain string is the id itself
            old_id = (
                enrollment.face_image.public_id
                if hasattr(enrollment.face_image, "public_id")
                else str(enrollment.face_image)
            )
            if old_id:
                cloudinary.uploader.destroy(old_id)
        except Exception:
            pass  # never block the upload if delete fails

    # ── 2. Compress with Pillow ───────────────────────────────────────────
    try:
        img = Image.open(pic)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Cap longest side at 800 px
        max_side = 800
        w, h = img.size
        if max(w, h) > max_side:
            ratio = max_side / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        # Step quality down until ≤ 100 KB
        buffer = io.BytesIO()
        quality = 85
        while quality >= 30:
            buffer.seek(0)
            buffer.truncate()
            img.save(buffer, format="JPEG", optimize=True, quality=quality)
            if buffer.tell() / 1024 <= 100:
                break
            quality -= 10

        buffer.seek(0)
    except Exception as e:
        messages.error(request, f"Image processing failed: {e}")
        return redirect('/profile/')

    # ── 3. Upload to Cloudinary & save public_id string ──────────────────
    # We always store the raw public_id string so both this view and
    # enroll_face.py (which also ends up storing via CloudinaryField)
    # resolve the same way in the Profile view.
    try:
        result = cloudinary.uploader.upload(
            buffer,
            folder="profile_pics",
            resource_type="image",
        )
        public_id = result["public_id"]

        # Assign as string — Django's CloudinaryField accepts a public_id
        # string and stores it correctly without re-uploading.
        enrollment.face_image = public_id
        enrollment.save(update_fields=["face_image"])

        cache.delete(f"profile_image_{request.user.id}")
        cache.delete(f"enrollment_{request.user.id}")

        messages.success(request, "Profile picture updated successfully!")
    except Exception as e:
        messages.error(request, f"Upload failed: {e}")

    return redirect('/profile/')


# ==============================
# HOME PAGE
# ==============================
def homePage(request):
    enrolled  = False
    isStaff   = False
    isSuperuser = False

    gym_notifications = cache.get("notifications")
    if gym_notifications is None:
        gym_notifications = list(
            GymNotification.objects.filter(is_active=True).values("icon", "message")
        )
        cache.set("notifications", gym_notifications, timeout=3600)

    plans = cache.get("membership_plans")
    if plans is None:
        plans = list(MembershipPlan.objects.all().values(
            "id", "plan", "price", "duration_days"
        ))
        cache.set("membership_plans", plans, timeout=3600)

    if request.user.is_authenticated:
        isStaff     = request.user.is_staff
        isSuperuser = request.user.is_superuser

        enrolled = cache.get(f"enrolled_{request.user.id}")
        if enrolled is None:
            enrolled = Enrollment.objects.filter(user=request.user).exists()
            cache.set(f"enrolled_{request.user.id}", enrolled, timeout=300)

    return render(request, "home.html", {
        "enrolled":           enrolled,
        "isStaff":            isStaff,
        "isSuperuser":        isSuperuser,
        "gym_notifications":  gym_notifications,
        "plans":              plans,
    })


# ==============================
# STATS API
# ==============================
def stats_api(request):
    total_users = Enrollment.objects.count()
    return JsonResponse({"total_users": total_users})


# ==============================
# CONTACT PAGE
# ==============================
def contact(request):
    if request.method == "POST":
        name    = request.POST.get('name', '').strip()
        number  = request.POST.get('number', '').strip()
        email   = request.POST.get('email', '').strip()
        message = request.POST.get('description', '').strip()

        if not number.isdigit() or len(number) != 10:
            messages.error(request, "Please enter a valid 10-digit phone number.")
            return redirect('/contact/')

        query = Contact(name=name, email=email, phonenumber=number, description=message)
        query.save()
        messages.success(request, "Thanks for contacting us — we'll get back to you soon!")
        return redirect('/contact/')

    return render(request, 'contact.html')


# ==============================
# LOGOUT
# ==============================
def handlelogout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('/')


# ==============================
# ENROLLMENT
# ==============================
@login_required
def enrollment(request):
    if Enrollment.objects.filter(user=request.user).exists():
        return redirect('/profile/')

    plans    = MembershipPlan.objects.all()
    trainers = Trainer.objects.all()

    if request.method == "POST":
        name       = request.POST.get('name', '').strip()
        email      = request.POST.get('email', '').strip()
        phone      = request.POST.get('phone', '').strip()
        gender     = request.POST.get('gender')
        plan_id    = request.POST.get('plan')
        trainer_id = request.POST.get('trainer')
        reference  = request.POST.get('reference', '').strip()
        address    = request.POST.get('address', '').strip()

        selected_trainer = None
        if trainer_id:
            try:
                selected_trainer = Trainer.objects.get(id=trainer_id)
            except Trainer.DoesNotExist:
                messages.error(request, "Selected trainer does not exist.")
                return redirect('/enrollment/')

        try:
            selected_plan = MembershipPlan.objects.get(id=plan_id)
        except MembershipPlan.DoesNotExist:
            messages.error(request, "Selected plan does not exist.")
            return redirect('/enrollment/')

        enroll = Enrollment(
            fullname=name,
            email=email,
            phone=phone,
            selectPlan=selected_plan,
            trainer=selected_trainer,
            gender=gender,
            reference=reference,
            address=address,
            user=request.user,
            paidAmount=0,
            pendingAmount=selected_plan.price,
        )
        enroll.save()
        # ── NEW: push notification to staff ──────────────────────────────────
        transaction.on_commit(lambda: notify_staff_new_enrollment(enroll))
        # ─────────────────────────────────────────────────────────────────────

        cache.delete(f"enrollment_{request.user.id}")
        cache.delete(f"profile_image_{request.user.id}")
        cache.delete(f"enrolled_{request.user.id}")
        cache.delete(f"enrollment_status_{request.user.id}")

        messages.success(
            request,
            "Welcome aboard! Your gym membership has been successfully activated."
        )
        return redirect('/profile/')

    return render(request, 'enrollment.html', {"plans": plans, "trainers": trainers})


# ==============================
# WORKOUT PAGE
# ==============================
def workout(request):
    return render(request, 'workout.html')


# ==============================
# PROFILE PAGE
# ==============================
# ==============================
# PROFILE PAGE
# ==============================
@login_required
def Profile(request):
    # ── Never cache model instances — CloudinaryField breaks on unpickling ──
    enrollment = (
        Enrollment.objects
        .filter(user=request.user)
        .select_related("selectPlan", "trainer")
        .first()
    )
    plans = cache.get("membership_plans")
    if plans is None:
        plans = list(MembershipPlan.objects.all().values("id", "plan", "price", "duration_days"))
        cache.set("membership_plans", plans, timeout=3600)

    image_url = None
    if enrollment and enrollment.face_image:
        image_url = cache.get(f"profile_image_{request.user.id}")
        if image_url is None:
            try:
                # CloudinaryField has .public_id when accessed on a live instance
                public_id = (
                    enrollment.face_image.public_id
                    if hasattr(enrollment.face_image, "public_id")
                    else str(enrollment.face_image)
                )
                if public_id:
                    image_url, _ = cloudinary_url(
                        public_id,
                        width=130, height=130,
                        crop="fill", gravity="face",
                        fetch_format="auto", quality="auto",
                    )
                    cache.set(f"profile_image_{request.user.id}", image_url, timeout=3600)
            except Exception:
                logger.exception("Failed to build Cloudinary URL for user %s", request.user.id)

    return render(request, "profile.html", {
        "enrollment":     enrollment,
        "image_url":      image_url,
        "is_expired":     enrollment.is_expired if enrollment else False,
        "days_remaining": enrollment.days_remaining if enrollment else 0,
        "plans":          plans,
    })


# ==============================
# ATTENDANCE PAGE
# ==============================
@login_required
def attendance_page(request):
    enrollment = Enrollment.objects.filter(user=request.user).first()
    if not enrollment:
        return redirect('/enrollment/')

    today = timezone.localdate()
    user  = request.user

    already_mark = Attendence_model.objects.filter(user=user, date=today).exists()

    all_attended = list(
        Attendence_model.objects
        .filter(user=user)
        .order_by('-date')
    )
    attended     = all_attended[:7]
    total_days   = len(all_attended)
    monthly_days = sum(
        1 for a in all_attended
        if a.date.year == today.year and a.date.month == today.month
    )

    return render(request, "attendence.html", {
        "enrollment":   enrollment,
        "records":      all_attended[:30],
        "already_mark": already_mark,
        "attended":     attended,
        "total_days":   total_days,
        "monthly_days": monthly_days,
        "today":        today,
    })


# ==============================
# WHATSAPP PAYMENT REMINDER
# ==============================
@login_required
@user_passes_test(is_staff)
def whatsapp_pending_users(request):
    pending = Enrollment.objects.filter(paymentStatus="Pending").select_related("selectPlan")

    pending_with_links = []
    for e in pending:
        msg = (
            f"Hello {e.fullname} ! Reminder from EnterGYM Bhilai: "
            f"your payment of ₹{e.pendingAmount} is pending. "
            f"Please clear your dues at your earliest convenience. "
            f"Thank you! – EnterGYM"
        )
        wa_link = f"https://wa.me/91{e.phone}?text={quote(msg)}"
        pending_with_links.append({"enrollment": e, "wa_link": wa_link})

    return render(request, "admin_whatsapp.html", {"pending": pending_with_links})


# ==============================
# PAYMENT MANAGEMENT PAGE
# ==============================
@login_required
@user_passes_test(is_staff)
def payment_management(request):
    status_filter = request.GET.get("filter", "pending")
    since = timezone.now() - timedelta(days=7)

    METHOD_LABELS = {"C": "Cash", "U": "UPI", "B": "UPI + Cash"}

    if status_filter == "done":
        qs = (
            Enrollment.objects
            .select_related("selectPlan", "trainer")
            .filter(created_at__gte=since, paymentStatus="Done")
            .order_by("-created_at")
        )
    else:
        qs = (
            Enrollment.objects
            .select_related("selectPlan", "trainer")
            .filter(paymentStatus="Pending")
            .order_by("-created_at")
        )

    rows = []
    for e in qs:
        rows.append({
            "id":                   e.id,
            "unique_id":            e.unique_id,
            "fullname":             e.fullname,
            "phone":                e.phone,
            "plan_name":            e.selectPlan.plan if e.selectPlan else "—",
            "plan_price":           float(e.selectPlan.price) if e.selectPlan else 0,
            "amount":               float(e.Amount),
            "paid":                 float(e.paidAmount),
            "pending":              float(e.pendingAmount),
            "payment_status":       e.paymentStatus,
            "payment_method":       e.paymentMethod or "",
            "payment_method_label": METHOD_LABELS.get(e.paymentMethod, "—"),
            "payment_date":         e.paymentDate.strftime("%Y-%m-%d") if e.paymentDate else "",
            "doj":                  e.doj.strftime("%d %b %Y") if e.doj else "—",
            "due_date":             e.DueDate.strftime("%b. %d, %Y") if e.DueDate else "—",
            "days_remaining":       e.days_remaining,
            "is_expired":           e.is_expired,
        })

    pending_count = Enrollment.objects.filter(paymentStatus="Pending").count()
    paid_count    = Enrollment.objects.filter(created_at__gte=since, paymentStatus="Done").count()
    total_count   = len(rows)

    return render(request, "payment_management.html", {
        "rows":                rows,
        "status_filter":       status_filter,
        "total_pending_amount": sum(r["pending"] for r in rows),
        "total_count":         total_count,
        "pending_count":       pending_count,
        "paid_count":          paid_count,
    })


# ==============================
# UPDATE PAYMENT (AJAX)
# ==============================
@login_required
@user_passes_test(is_staff)
@require_POST
def update_payment(request):
    try:
        data           = json.loads(request.body)
        enrollment_id  = int(data.get("enrollment_id", 0))
        paid_amount    = float(data.get("paid_amount", 0))
        payment_method = data.get("payment_method", "").strip()
        payment_date_s = data.get("payment_date", "").strip() or None

        if paid_amount < 0:
            return JsonResponse({"error": "Paid amount cannot be negative."}, status=400)
        if payment_method not in ("C", "U", "B", ""):
            return JsonResponse({"error": "Invalid payment method."}, status=400)

        enrollment = Enrollment.objects.select_related("selectPlan", "user").get(pk=enrollment_id)

        if not enrollment.user_id:
            return JsonResponse({"error": "Invalid enrollment."}, status=403)

        plan_price     = float(enrollment.selectPlan.price) if enrollment.selectPlan else float(enrollment.Amount)
        paid_amount    = min(paid_amount, plan_price)
        pending_amount = max(plan_price - paid_amount, 0)

        enrollment.paidAmount    = paid_amount
        enrollment.pendingAmount = pending_amount
        enrollment.paymentStatus = "Done" if pending_amount == 0 else "Pending"
        enrollment.paymentMethod = payment_method or None

        if payment_date_s:
            enrollment.paymentDate = date.fromisoformat(payment_date_s)
        elif paid_amount > 0 and not enrollment.paymentDate:
            enrollment.paymentDate = timezone.localdate()

        enrollment.save(update_fields=[
            "paidAmount", "pendingAmount", "paymentStatus",
            "paymentMethod", "paymentDate",
        ])

        cache.delete("admin_revenue")
        cache.delete("admin_revenue_data")
        cache.delete(f"enrollment_{enrollment.user_id}")
        cache.delete(f"enrollment_status_{enrollment.user_id}")

        METHOD_LABELS = {"C": "Cash", "U": "UPI", "B": "UPI + Cash"}

        return JsonResponse({
            "ok":                   True,
            "enrollment_id":        enrollment.id,
            "paid":                 float(enrollment.paidAmount),
            "pending":              float(enrollment.pendingAmount),
            "payment_status":       enrollment.paymentStatus,
            "payment_method_label": METHOD_LABELS.get(enrollment.paymentMethod, "—"),
            "payment_date":         enrollment.paymentDate.strftime("%d %b %Y") if enrollment.paymentDate else "—",
        })

    except Enrollment.DoesNotExist:
        return JsonResponse({"error": "Enrollment not found."}, status=404)
    except (ValueError, KeyError) as e:
        return JsonResponse({"error": f"Invalid data: {e}"}, status=400)
    except Exception:
        logger.exception("Unexpected error in update_payment")
        return JsonResponse({"error": "An internal error occurred."}, status=500)


# ==============================
# TODAY'S ATTENDANCE (STAFF)
# ==============================
@login_required
@user_passes_test(is_staff)
def today_attendance(request):
    today     = timezone.localdate()
    cache_key = f"today_attendance_{today}"

    cached = cache.get(cache_key)
    if cached:
        return render(request, "today_attendance.html", cached)

    records = (
        Attendence_model.objects
        .filter(date=today)
        .select_related("user__enrollment__selectPlan", "user__enrollment__trainer")
        .order_by("timestamp")
    )

    morning = []
    evening = []

    for rec in records:
        enrollment = getattr(rec.user, "enrollment", None)

        # ── Build Cloudinary image URL (server-side, never cached in context) ──
        image_url = None
        if enrollment and enrollment.face_image:
            try:
                public_id = (
                    enrollment.face_image.public_id
                    if hasattr(enrollment.face_image, "public_id")
                    else str(enrollment.face_image)
                )
                if public_id:
                    image_url, _ = cloudinary_url(
                        public_id,
                        width=60, height=60,
                        crop="fill", gravity="face",
                        fetch_format="auto", quality="auto",
                    )
            except Exception:
                logger.exception("Cloudinary URL error for user %s", rec.user.id)

        entry = {
            "id":             rec.id,
            "time":           rec.timestamp.strftime("%I:%M %p"),
            "name":           enrollment.fullname if enrollment else rec.user.username,
            "unique_id":      enrollment.unique_id if enrollment else "—",
            "image_url":      image_url,
            "pending_amount": float(enrollment.pendingAmount) if enrollment else 0,
            "due_date":       enrollment.DueDate.strftime("%d %b %Y") if enrollment and enrollment.DueDate else "—",
            "is_expired":     enrollment.is_expired if enrollment else False,
            "phone":          enrollment.phone if enrollment else "—",
            "address":        enrollment.address if enrollment else "—",
            "plan":           enrollment.selectPlan.plan if enrollment and enrollment.selectPlan else "—",
            "plan_price":     float(enrollment.selectPlan.price) if enrollment and enrollment.selectPlan else 0,
            "trainer":        enrollment.trainer.name if enrollment and enrollment.trainer else "No Trainer",
            "gender":         enrollment.get_gender_display() if enrollment else "—",
            "doj":            enrollment.doj.strftime("%d %b %Y") if enrollment and enrollment.doj else "—",
            "payment_status": enrollment.paymentStatus if enrollment else "—",
            "days_remaining": enrollment.days_remaining if enrollment else 0,
            "payment_date":   enrollment.paymentDate.strftime("%d %b %Y") if enrollment and enrollment.paymentDate else "—",
        }
        if rec.timestamp.hour < 14:
            morning.append(entry)
        else:
            evening.append(entry)

    context = {
      "sections": [
          ("Morning", "🌅", morning),
          ("Evening", "🌆", evening),
        ],
        "today": today,
        "total": len(morning) + len(evening),
    }

    cache.set(cache_key, context, timeout=120)
    return render(request, "today_attendance.html", context)

# ==============================
# RENEW MEMBERSHIP
# ==============================
@login_required
@require_POST
def renew_membership(request):
    enrollment = get_object_or_404(Enrollment, user=request.user)

    plan_id = request.POST.get("plan")
    try:
        selected_plan = MembershipPlan.objects.get(id=plan_id)
    except MembershipPlan.DoesNotExist:
        messages.error(request, "Invalid plan selected.")
        return redirect('/profile/')

    # ── If plan still active, extend from current DueDate
    # ── If already expired, start fresh from today
    today = timezone.now().date()
    if enrollment.DueDate and enrollment.DueDate > today:
        new_due_date = enrollment.DueDate + timedelta(days=selected_plan.duration_days)
    else:
        new_due_date = today + timedelta(days=selected_plan.duration_days)

    enrollment.selectPlan    = selected_plan
    enrollment.Amount        = selected_plan.price
    enrollment.paidAmount    = 0
    enrollment.pendingAmount = selected_plan.price
    enrollment.paymentStatus = "Pending"
    enrollment.paymentMethod = None
    enrollment.paymentDate   = None
    enrollment.DueDate       = new_due_date

    enrollment.save(update_fields=[
        "selectPlan", "Amount", "paidAmount", "pendingAmount",
        "paymentStatus", "paymentMethod", "paymentDate", "DueDate",
    ])

    cache.delete(f"enrollment_{request.user.id}")
    cache.delete(f"enrollment_status_{request.user.id}")
    cache.delete("admin_revenue")
    cache.delete("admin_revenue_data")

    messages.success(request, f"Membership renewed with {selected_plan.plan}! Please complete your payment.")
    return redirect('/profile/')

# ==============================
# FREEZE MEMBERSHIP (Staff Only)
# ==============================

@login_required
@user_passes_test(is_staff)
def freeze_membership(request):
    """
    GET  — shows full member list with search by unique_id
    """
    query = request.GET.get("q", "").strip()

    qs = (
        Enrollment.objects
        .select_related("selectPlan")
        .order_by("fullname")
    )

    if query:
        qs = qs.filter(unique_id=query)

    paginator  = Paginator(qs, 20)          # 20 members per page
    page_num   = request.GET.get("page", 1)
    page_obj   = paginator.get_page(page_num)

    return render(request, "freeze_membership.html", {
        "page_obj": page_obj,
        "query":    query,
    })


@login_required
@user_passes_test(is_staff)
@require_POST
def freeze_membership_apply(request):
    """
    POST — applies the freeze (extends DueDate by N days).
    Redirects back to the list, preserving search query if any.
    """
    enrollment_id = request.POST.get("enrollment_id", "").strip()
    days_raw      = request.POST.get("days", "").strip()
    back_query    = request.POST.get("q", "").strip()

    redirect_url = "/freeze-membership/"
    if back_query:
        redirect_url += f"?q={back_query}" 

    # ── Validate days ──────────────────────────────────────────────────────
    try:
        days = int(days_raw)
        if days < 1 or days > 365:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, "Invalid number of days. Enter a value between 1 and 365.")
        return redirect(redirect_url)

    # ── Fetch enrollment ───────────────────────────────────────────────────
    try:
        enrollment = Enrollment.objects.select_related("user").get(pk=enrollment_id)
    except Enrollment.DoesNotExist:
        messages.error(request, "Member not found.")
        return redirect(redirect_url)

    # ── Extend DueDate ─────────────────────────────────────────────────────
    if not enrollment.DueDate:
        messages.error(
            request,
            f"Member {enrollment.unique_id} has no due date set. "
            "Please set a plan before freezing."
        )
        return redirect(redirect_url)

    old_due          = enrollment.DueDate
    new_due          = old_due + timedelta(days=days)
    enrollment.DueDate = new_due
    enrollment.save(update_fields=["DueDate"])

    # Bust relevant caches
    cache.delete(f"enrollment_{enrollment.user_id}")
    cache.delete(f"enrollment_status_{enrollment.user_id}")

    messages.success(
        request,
        f"✅ {enrollment.fullname} ({enrollment.unique_id}) — due date extended by {days} day{'s' if days != 1 else ''}: "
        f"{old_due.strftime('%d %b %Y')} → {new_due.strftime('%d %b %Y')}."
    )
    return redirect(redirect_url)

# ==============================
# DOWNLOAD APP PAGE
# ==============================
def download_app(request):
    return render(request, 'download.html')