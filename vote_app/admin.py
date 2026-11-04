from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Profile, Candidate, ElectionState, Vote
from django.utils.html import format_html

# Personnalisation basique de l'interface
admin.site.site_header = "ÉLECTION DU GOUVERNEUR AESP - Système de Vote"
admin.site.site_title = "AESP Voting Admin"
admin.site.index_title = "Tableau de bord"

class DejaConnecteFilter(admin.SimpleListFilter):
    """Filtre : s'est déjà connecté au moins une fois / jamais connecté."""
    title = 'Déjà connecté'
    parameter_name = 'deja_connecte'

    def lookups(self, request, model_admin):
        return (('oui', 'Oui, au moins une fois'), ('non', 'Non, jamais connecté'))

    def queryset(self, request, queryset):
        if self.value() == 'oui':
            return queryset.filter(user__last_login__isnull=False)
        if self.value() == 'non':
            return queryset.filter(user__last_login__isnull=True)
        return queryset


@admin.register(Profile)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('matricule','get_fullname','telephone', 'a_deja_connecte', 'derniere_connexion', 'role', 'status', 'campus', 'cycle', 'specialite', 'niveau', 'is_connected', 'last_activity', 'is_actually_connected', 'has_active_session', 'session_expires', 'session_token', 'has_voted', 'is_admin', 'photo', 'recu', 'verification_source', 'verification_score')
    list_filter = (DejaConnecteFilter, 'matricule', 'role', 'status', 'cycle', 'niveau', 'campus', 'verification_source')
    readonly_fields = ('recu_hash', 'verification_source', 'verification_score', 'verification_note', 'verified_at')
    search_fields = ('cycle', 'niveau',)

    def get_fullname(self, obj):
        return obj.get_fullname()

    @admin.display(boolean=True, description='Déjà connecté', ordering='user__last_login')
    def a_deja_connecte(self, obj):
        return obj.has_logged_in

    @admin.display(description='Dernière connexion', ordering='user__last_login')
    def derniere_connexion(self, obj):
        return obj.user.last_login
    

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'cycle', 'specialite', 'niveau', 'campus', 'votes', 'bureau_name', 'bureau_color', 'photo_link' , 'programme_url')
    search_fields = ('nom', 'prenom', 'bureau_name', 'specialite')
    readonly_fields = ['votes']

    fieldsets = (
        ('Informations Personnelles', {
            'fields': ('nom', 'prenom', 'cycle', 'specialite', 'niveau')
        }),
        ('Campagne Électorale', {
            'fields': ('slogan', 'photo_url', 'programme_pdf', 'bureau_name', 'bureau_color')
        }),
        ('Statistiques', {
            'fields': ('votes', 'is_active')
        }),
    )


    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="width: 100px; height: 100px; object-fit: cover;" />', obj.photo.url)
        return "Aucune photo"
    
    photo_preview.short_description = "Aperçu de la photo"
    
    # Configuration pour les uploads
    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }
    
    
@admin.register(ElectionState)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('status',)
    list_filter = ('status',)
    search_fields = ('title',)

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('profile', 'candidate', 'voted_at')
    list_filter = ('voted_at',)
    readonly_fields = ('voted_at',)