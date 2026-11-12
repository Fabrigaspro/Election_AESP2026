# election_project/urls.py

from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('vote_app.urls')), # Inclure les URLs de vote_app
]

from django.views.generic import TemplateView

urlpatterns += [
    path('serviceworker.js', TemplateView.as_view(
        template_name='serviceworker.js', content_type='application/javascript')),
    path('offline/', TemplateView.as_view(template_name='offline.html')),
]

# Servir les fichiers médias en mode DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
