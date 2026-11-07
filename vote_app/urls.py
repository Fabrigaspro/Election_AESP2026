# vote_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Vue principale
    path('', views.index, name='index'),

    # API d'authentification
    path('api/register/', views.register_view, name='api_register'),
    path('api/cycle-options/', views.get_cycle_options, name='cycle_options'),
    path('api/login/', views.login_view, name='api_login'),
    path('api/logout/', views.logout_view, name='api_logout'),
    path('api/check_session/', views.check_session_view, name='api_check_session'),
    path('api/change_password/', views.change_password_view, name='change_password'),
    path('api/login-qr/', views.login_qr_view, name='login_qr'),
    path('api/login-options/', views.login_options_view, name='api_login_options'),
    # API de données
    path('api/dashboard_data/', views.dashboard_data_view, name='api_dashboard_data'),
    path('api/vote/', views.vote_view, name='api_vote'),

    # API d'administration
    path('api/users/<int:user_id>/', views.manage_user_status_view, name='api_manage_user'),
    path('api/users/bulk/', views.bulk_users_view, name='api_bulk_users'),
    path('api/candidates/', views.manage_candidates_view, name='api_manage_candidates'),
    path('api/candidates/<int:candidate_id>/', views.manage_candidate_detail_view, name='api_manage_candidate_detail'),
    path('api/election/', views.manage_election_view, name='api_manage_election'),
    path('api/election/reset/', views.reset_election_view, name='reset_election'),
]