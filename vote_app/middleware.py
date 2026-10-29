# middleware.py
from django.contrib.auth import logout
from .models import Profile


class SessionManagementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # Les comptes staff/superuser (admin Django) ne passent pas par cette logique
        if user.is_authenticated and not (user.is_staff or user.is_superuser):
            try:
                profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                logout(request)
            else:
                session_token = request.session.get('session_token')

                if (not session_token or session_token != profile.session_token) and not profile.is_admin:
                    logout(request)
                elif not profile.has_active_session and not profile.is_admin:
                    profile.invalidate_session()
                    logout(request)
                else:
                    if not profile.is_connected:
                        profile.is_connected = True
                        profile.save(update_fields=['is_connected'])
                    profile.update_activity()

        return self.get_response(request)