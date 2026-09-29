from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send expiry reminder push notifications to members'

    def handle(self, *args, **kwargs):
        from AuthFit.notifications import send_expiry_reminders
        count = send_expiry_reminders()
        self.stdout.write(
            self.style.SUCCESS(f'Expiry reminders sent for {count} enrollments')
        )