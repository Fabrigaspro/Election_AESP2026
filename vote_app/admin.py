from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Profile, Candidate, ElectionState, Vote
from django.utils.html import format_html

# Personnalisation basique de l'interface
admin.site.site_header = "ELECTION AESP - Système de Vote"
admin.site.site_title = "AESP Voting Admin"
admin.site.index_title = "Tableau de bord"

@admin.register(Profile)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('matricule','get_fullname','telephone', 'role', 'status', 'campus', 'cycle', 'specialite', 'niveau', 'is_connected', 'last_activity', 'is_actually_connected', 'has_active_session', 'session_expires', 'session_token', 'has_voted', 'is_admin', 'photo', 'recu')
    list_filter = ('matricule', 'role', 'status', 'cycle', 'niveau', 'campus')
    search_fields = ('cycle', 'niveau',)

    def get_fullname(self, obj):
        return obj.get_fullname()
    

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