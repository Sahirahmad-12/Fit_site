from django.utils import timezone
from AuthFit.models import Enrollment, Attendence


def mark_attendance(unique_id):
    """
    Marks attendance for a user using unique_id.
    Prevents duplicate attendance for the same day.
    """

    try:
        enrollment = Enrollment.objects.get(unique_id=unique_id)
        user = enrollment.user

        today = timezone.localdate()

        # 🔹 Prevent duplicate attendance
        attendance, created = Attendence.objects.get_or_create(
            user=user,
            date=today
        )

        if created:
            return {
                "status": "success",
                "message": "Attendance marked successfully"
            }
        else:
            return {
                "status": "exists",
                "message": "Attendance already marked today"
            }

    except Enrollment.DoesNotExist:
        return {
            "status": "error",
            "message": "User not found"
        }
