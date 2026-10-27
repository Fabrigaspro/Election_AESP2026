# middleware.py
from .models import Profile

class SessionManagementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("*"*30)
        print("*"*30)
        print("request.user.is_authenticated", request.user.is_authenticated)
        print("*"*30)
        print("*"*30)
        if request.user.is_authenticated:
            try:
                profile = Profile.objects.get(user=request.user)
                profile.is_connected = True 
                profile.save()
                print("profile.is_admin : ", profile.is_admin)
                # Vérifier la validité de la session
                session_token = request.session.get('session_token')
                # Si pas de token ou token invalide
                if (not session_token or session_token != profile.session_token) and not profile.is_admin:
                    from django.contrib.auth import logout
                    logout(request)
                    # Ne pas retourner d'erreur ici, laisser la redirection normale
                
                # Si token valide mais session expirée
                elif (not profile.has_active_session) and not profile.is_admin:
                    from django.contrib.auth import logout
                    profile.invalidate_session()
                    logout(request)
                
                else:
                    # Session valide - mettre à jour l'activité
                    profile.update_activity()
                    
            except Profile.DoesNotExist:
                # Pas de profil = déconnexion
                from django.contrib.auth import logout
                logout(request)
        
        response = self.get_response(request)
        return response