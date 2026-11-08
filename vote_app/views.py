# vote_app/views.py

import json
import os
from django.conf import settings
from django.http import JsonResponse, HttpResponse
import os
import json
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Profile, Candidate, ElectionState, Vote
from django.utils import timezone
from datetime import timedelta
from django.db import transaction, IntegrityError
from django.core.cache import cache
from . import receipt_verifier
import re
import unicodedata
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# Méthodes utilitaires pour les choix dynamiques
def get_specialites_by_cycle(cycle):
    """Retourne les spécialités disponibles pour un cycle donné"""
    specialites = {
        'bts': Profile.SPECIALITE_BTS,
        'hnd': Profile.SPECIALITE_HND,
        'lipro': Profile.SPECIALITE_LICENCEPRO,
        'litech': Profile.SPECIALITE_LICENCETECH,
        'bachelor': Profile.SPECIALITE_BACHELOR,
        'master': Profile.SPECIALITE_MASTER,
        'ingenieur': Profile.SPECIALITE_INGENIEUR,
    }
    return specialites.get(cycle, [])

def get_niveaux_by_cycle(cycle):
    """Retourne les niveaux disponibles pour un cycle donné"""
    niveaux = {
        'bts': [1, 2],
        'hnd': [1, 2],

        'lipro': [3],
        'litech': [3],
        'bachelor': [1, 2, 3],

        'master': [4, 5],

        'ingenieur': [1, 2, 3, 4, 5],
    }
    return niveaux.get(cycle, [])

def get_cycle_options(request):
    """API pour récupérer les spécialités et niveaux par cycle"""
    cycle = request.GET.get('cycle')
    
    if not cycle:
        return JsonResponse({'error': 'Cycle non spécifié'}, status=400)
    
    specialites = get_specialites_by_cycle(cycle)

    if cycle != 'ingenieur':
        niveaux = get_niveaux_by_cycle(cycle)
        
        return JsonResponse({
            'specialites': specialites,
            'niveaux': niveaux
        })
    else:        
        return JsonResponse({
            'specialites': specialites,
            'niveaux12': [1, 2],
            'niveaux345': [3, 4, 5]
        })

def _default_password_candidates(user):
    """Mots de passe par défaut possibles pour ce compte.

    Règle : 2 premières lettres de chaque mot du nom, puis de chaque mot du prénom,
    en MAJUSCULES, sans accent ni espace (KAMGA TCHOUA / MARIE LAURE -> KATCMALA).
    On teste les deux ordres (first_name/last_name) car l'import et l'inscription
    ne rangent pas forcément nom et prénom dans le même champ.
    """
    def words_variants(text):
        norm = unicodedata.normalize('NFKD', text or '')
        norm = ''.join(c for c in norm if not unicodedata.combining(c)).upper()
        by_space = [re.sub(r'[^A-Z0-9]', '', w) for w in norm.split()]
        by_punct = re.split(r'[^A-Z0-9]+', norm)
        return [[w for w in v if w] for v in (by_space, by_punct)]

    def initials(words):
        return ''.join(w[:2] for w in words)

    found = set()
    for a, b in ((user.first_name, user.last_name), (user.last_name, user.first_name)):
        for wa in words_variants(a):
            for wb in words_variants(b):
                code = initials(wa) + initials(wb)
                if code:
                    found.add(code)
    return found

def _is_default_password(user, password):
    return password in _default_password_candidates(user)


# Vue pour servir la page HTML principale
def index(request):
    return render(request, 'vote_app/index.html')

# ===============================================
# FONCTIONS HELPER
# ===============================================

def is_user_admin(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_admin

# Convertit un objet User/Profile en dictionnaire pour la réponse JSON
def user_to_dict(user):
    """Convertit un objet User/Profile en dictionnaire pour la réponse JSON."""
    if not hasattr(user, 'profile') and not is_user_admin(user):
        Profile.objects.create(user=user) # Crée un profil si manquant
    return {
        'id': user.id,
        'nom': user.last_name,
        'prenom': user.first_name,
        'matricule': user.username,
        'campus': user.profile.campus,
        'cycle': user.profile.cycle,
        'cycle_display': user.profile.get_cycle_display(),
        'specialite': user.profile.specialite,
        'niveau': user.profile.niveau,
        'telephone': user.profile.telephone,
        'photo_url': user.profile.photo.url if user.profile.photo else None,
        'recu_url': user.profile.recu.url if user.profile.recu else None,
        'status': user.profile.status,
        'has_voted': user.profile.has_voted,
        'is_admin': user.profile.is_admin,
        'verification_source': user.profile.verification_source,
        'verification_score': user.profile.verification_score,
        'verification_note': user.profile.verification_note,
        'has_logged_in': user.last_login is not None,   # s'est déjà connecté au moins une fois
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }


def validate_image_upload(file_obj, allowed_exts=None, max_size_mb=10):
    """Valide un fichier uploadé comme image.
    - allowed_exts: liste d'extensions sans point, ex: ['jpg','png']
    - max_size_mb: taille maximale autorisée en mégaoctets
    Retourne (True, None) si OK, sinon (False, message)
    """
    if not file_obj:
        return True, None

    if allowed_exts is None:
        allowed_exts = ['jpg', 'jpeg', 'png']

    # Vérifier la taille
    try:
        size = getattr(file_obj, 'size', None)
        if size is not None and size > max_size_mb * 1024 * 1024:
            return False, f'Fichier trop volumineux (>{max_size_mb} MB).'
    except Exception:
        pass

    # Vérifier le content_type s'il existe
    content_type = getattr(file_obj, 'content_type', '') or ''
    if content_type:
        if not content_type.startswith('image/') and not any(ext in content_type for ext in allowed_exts):
            return False, 'Type de fichier non autorisé (seuls jpg, jpeg et png sont autorisés).'

    # Vérifier l'extension
    name = getattr(file_obj, 'name', '') or ''
    if '.' in name:
        ext = name.rsplit('.', 1)[1].lower()
        if ext not in allowed_exts:
            return False, f'Extension non autorisée: .{ext}.'
    else:
        # Pas d'extension fournie
        return False, 'Nom de fichier sans extension.'

    return True, None


# ===============================================
# MOT DE PASSE PAR DÉFAUT / CHANGEMENT DE MOT DE PASSE
# ===============================================

def _default_password_part(text):
    """2 premières lettres de chaque mot, en MAJUSCULES, sans accent ni espace."""
    text = unicodedata.normalize('NFD', text or '')
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    words = re.findall(r'[A-Za-z]+', text)
    return ''.join(w[:2] for w in words).upper()


def default_password_candidates(user):
    """Mots de passe par défaut possibles d'un compte (nom+prénom ou prénom+nom,
    car l'ordre dépend de la façon dont le compte a été créé)."""
    a = _default_password_part(user.first_name)
    b = _default_password_part(user.last_name)
    return {a + b, b + a} - {''}


def is_default_password(user, raw_password):
    """True si le mot de passe saisi est le mot de passe par défaut du compte."""
    return bool(raw_password) and raw_password in default_password_candidates(user)


def _change_password_rate_limited(request):
    """Limite les essais d'ancien mot de passe (par utilisateur, 10 par 15 min)."""
    key = f'chgpwd_attempts:{request.user.id}'
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, 900)
    return attempts > 10

# ===============================================
# VUES API  electionStatusMessage
# ===============================================

def _client_ip(request):
    """IP du client derrière le proxy Railway (dernier saut ajouté par le proxy)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', 'inconnue')


def _register_rate_limited(request):
    """Limite le nombre d'inscriptions par IP et par heure (coût IA + faux comptes)."""
    limit = getattr(settings, 'REGISTER_MAX_PER_IP_PER_HOUR', 15)
    key = f'register_attempts:{_client_ip(request)}'
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, 3600)
    return attempts > limit


@csrf_exempt # Enregistrement d'un nouvel étudiant, avec vérification IA du reçu
def register_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    data = request.POST
    matricule = ''.join((data.get('matricule') or '').split()).upper()   # sans espaces, en majuscules
    nom = (data.get('nom') or '').strip()
    prenom = (data.get('prenom') or '').strip()
    password = data.get('password')

    if not matricule:
        return JsonResponse({'error': 'Matricule manquant.'}, status=400)
    if not nom or not prenom:
        return JsonResponse({'error': 'Nom et prénom obligatoires.'}, status=400)
    if not password:
        return JsonResponse({'error': 'Mot de passe manquant.'}, status=400)

    if User.objects.filter(username__iexact=matricule).exists():
        return JsonResponse({'error': 'Ce matricule est déjà utilisé.'}, status=400)

    # Valider les fichiers uploadés (photo, recu)
    photo_file = request.FILES.get('photo')
    recu_file = request.FILES.get('recu')
    if not photo_file:
        return JsonResponse({'error': 'La photo de profil est obligatoire.'}, status=400)
    if not recu_file:
        return JsonResponse({'error': 'Le reçu est obligatoire.'}, status=400)

    ok, msg = validate_image_upload(photo_file)
    if not ok:
        return JsonResponse({'error': f'Photo invalide: {msg}'}, status=400)

    ok, msg = validate_image_upload(recu_file)
    if not ok:
        return JsonResponse({'error': f'Reçu invalide: {msg}'}, status=400)

    if _register_rate_limited(request):
        return JsonResponse({'error': 'Trop de tentatives. Réessayez dans une heure.'}, status=429)

    # --- Analyse du reçu : lecture par l'IA puis comparaison avec le formulaire ---
    try:
        jpeg_bytes, recu_hash = receipt_verifier.prepare_image(recu_file)
    except receipt_verifier.ReceiptImageError as e:
        return JsonResponse({'error': f'Reçu invalide: {e}'}, status=400)

    # Un même reçu ne peut servir qu'à un seul compte
    if Profile.objects.filter(recu_hash=recu_hash).exists():
        return JsonResponse({
            'error': 'Ce reçu a déjà été utilisé pour une autre inscription. '
                     'Si c\'est une erreur, contactez l\'administrateur.'
        }, status=400)

    cycle = data.get('cycle', '')
    specialite = data.get('specialite', '')
    specialite_label = dict(get_specialites_by_cycle(cycle)).get(specialite, specialite)
    verdict = receipt_verifier.verify_receipt({
        'nom': nom, 'prenom': prenom, 'matricule': matricule,
        'cycle': cycle, 'niveau': data.get('niveau', ''), 'campus': data.get('campus', ''),
        'specialite': specialite, 'specialite_label': specialite_label,
    }, jpeg_bytes)

    # Refus immédiat : l'étudiant corrige et renvoie, rien n'est enregistré
    if verdict.rejected:
        return JsonResponse({
            'error': 'Inscription refusée : votre reçu ne correspond pas aux informations saisies. '
                     'Corrigez les points ci-dessous puis réessayez.',
            'reasons': verdict.rejection_reasons(),
        }, status=400)

    auto_validated = verdict.validated
    user = None
    try:
        with transaction.atomic():
            # Crée l'utilisateur Django
            user = User.objects.create_user(
                username=matricule,
                password=password,
                first_name=nom,
                last_name=prenom
            )

            try:
                niveau = int(data.get('niveau') or 0)
            except (TypeError, ValueError):
                niveau = 0

            # Crée le profil associé
            Profile.objects.create(
                user=user,
                campus=data.get('campus', ''),
                cycle=data.get('cycle', ''),
                specialite=data.get('specialite', ''),
                niveau=niveau,
                telephone=data.get('telephone', ''),
                photo=photo_file,
                recu=recu_file,
                status='validated' if auto_validated else 'pending',
                recu_hash=recu_hash,
                verification_source='ai' if auto_validated else '',
                verification_score=verdict.score,
                verification_note=verdict.note(),
                verified_at=timezone.now() if auto_validated else None,
            )

    except IntegrityError:
        return JsonResponse({'error': 'Erreur base de données lors de la création du compte.'}, status=500)
    except Exception:
        # tentative de suppression au cas où un enregistrement partiel aurait persisté
        try:
            if user is not None:
                user.delete()
        except Exception:
            pass
        return JsonResponse({'error': 'Problème lors de la création du profil. Connexion instable'}, status=400)

    if auto_validated:
        return JsonResponse({
            'success': 'Inscription validée automatiquement.',
            'status': 'validated',
            'message': 'Votre reçu a été vérifié : votre compte est validé. '
                       'Vous pouvez maintenant vous connecter.',
        })

    return JsonResponse({
        'success': 'Inscription enregistrée, en attente de vérification.',
        'status': 'pending',
        'message': 'Votre inscription est enregistrée, mais l\'analyse automatique du reçu est '
                   'momentanément indisponible. Un administrateur va le vérifier.',
        'reasons': verdict.failed_reasons(),
    })

def _open_session(request, user, profile, method='password'):
    """Ouvre la session Django de l'utilisateur (token de session, activité, login())."""
    session_token = profile.generate_session_token()
    request.session['session_token'] = session_token
    request.session['user_id'] = user.id
    request.session['login_method'] = method
    profile.last_activity = timezone.now()
    profile.save(update_fields=['last_activity'])
    login(request, user)


def login_options_view(request):
    """Public : indique à la page de connexion quels modes de connexion sont ouverts."""
    return JsonResponse({
        'password_login_enabled': ElectionState.load().password_login_enabled,
        'qr_login_enabled': getattr(settings, 'QR_LOGIN_ENABLED', True),
    })


@csrf_exempt # Connection d'un utilisateur
def login_view(request):
    print("Connexion en cours demarrée.......")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            matricule = (data.get('matricule') or '').strip()
            password = data.get('password')
            existing = User.objects.filter(username__iexact=matricule).first()
            if existing:
                matricule = existing.username        # le vrai identifiant enregistré, avec sa casse d'origine
            
            user = authenticate(username=matricule, password=password)
            if user is not None:
                # Générer un nouveau token de session
                profile, created = Profile.objects.get_or_create(user=user)
                
                print("profile.has_active_session : ", profile.has_active_session)
                # Vérifier s'il y a une session ACTIVE (non expirée)
                if profile.has_active_session and not profile.is_admin:
                    return JsonResponse({
                        'success': False,
                        'error': 'Compte déjà connecté sur un autre appareil. Déconnectez-vous d\'abord ou attendez que la session expire.'
                    }, status=400)
                
                # Interrupteur admin : connexion par identifiants coupée pour les étudiants (les admins passent toujours)
                if not profile.is_admin and not ElectionState.load().password_login_enabled:
                    return JsonResponse({
                        'success': False,
                        'error': "La connexion par matricule et mot de passe est temporairement désactivée par l'administrateur. "
                                 "Utilisez le QR code de votre reçu."
                    }, status=403)

                _open_session(request, user, profile)

                try:
                    return JsonResponse({
                        'success': True,
                        'user': user_to_dict(user),
                        'message': 'Connexion réussie',
                        # Permet au site de proposer de changer le mot de passe par défaut
                        'using_default_password': (not profile.is_admin) and is_default_password(user, password),
                    })
                except Exception as e:
                    print("ereur de la sortie JsonResponse : ", e)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Matricule ou mot de passe incorrect'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur de connexion: {str(e)}'
            }, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

# ===============================================
# 2e MODE DE CONNEXION : QR CODE DU REÇU
# ===============================================
QR_SIGNATURE_RE = re.compile(r'^[0-9a-fA-F]{64}$')


def _qr_login_rate_limited(request):
    """Limite les essais de connexion par reçu : 15 par IP et par 15 minutes."""
    key = f'qr_login_attempts:{_client_ip(request)}'
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, 900)
    return attempts > getattr(settings, 'QR_LOGIN_MAX_PER_IP', 15)


@csrf_exempt  # Connexion avec le QR code du reçu : le texte du QR est lu par le téléphone (scan en direct)
def login_qr_view(request):
    """Reçoit le contenu du QR scanné ({"qr": "MATRICULE|AAAA/AAAA|signature"}) — ou, en secours,
    une image du reçu (champ multipart « recu ») dont le QR est décodé côté serveur."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    if not getattr(settings, 'QR_LOGIN_ENABLED', True):
        return JsonResponse({'error': 'La connexion par reçu est désactivée.'}, status=403)
    if _qr_login_rate_limited(request):
        return JsonResponse({'error': 'Trop de tentatives. Réessayez dans quelques minutes.'}, status=429)

    # 1) contenu du QR code
    if request.content_type == 'application/json':
        try:
            qr_text = str(json.loads(request.body).get('qr') or '').strip()
        except (TypeError, ValueError, AttributeError):
            return JsonResponse({'error': 'Requête invalide.'}, status=400)
        if len(qr_text) > 300:
            return JsonResponse({'error': "Ce QR code n'est pas celui d'un reçu AESP valide."}, status=400)
    else:
        recu_file = request.FILES.get('recu')
        if not recu_file:
            return JsonResponse({'error': 'QR code manquant.'}, status=400)
        ok, msg = validate_image_upload(recu_file)
        if not ok:
            return JsonResponse({'error': f'Reçu invalide: {msg}'}, status=400)
        try:
            jpeg_bytes, _ = receipt_verifier.prepare_image(recu_file)
        except receipt_verifier.ReceiptImageError as e:
            return JsonResponse({'error': f'Reçu invalide: {e}'}, status=400)
        qr_text = receipt_verifier.decode_qr(jpeg_bytes) or ''

    qr = receipt_verifier.parse_qr_payload(qr_text)
    if not qr['qr_raw']:
        return JsonResponse({'error': 'QR code introuvable ou illisible. Réessayez en le cadrant bien.'}, status=400)
    matricule = ''.join((qr['qr_matricule'] or '').split()).upper()
    if not matricule or not qr['qr_signature'] or not QR_SIGNATURE_RE.match(qr['qr_signature']):
        return JsonResponse({'error': "Ce QR code n'est pas celui d'un reçu AESP valide."}, status=400)

    # 2) année académique du scrutin
    expected_year = receipt_verifier.normalize_year(getattr(settings, 'ACADEMIC_YEAR', ''))
    if expected_year and qr['qr_annee_academique'] != expected_year:
        return JsonResponse({'error': f"Ce reçu n'est pas celui de l'année académique {expected_year}."}, status=400)

    # 3) le matricule doit correspondre à un compte existant (jamais un compte administrateur)
    user = User.objects.filter(username__iexact=matricule).first()
    if user is None:
        return JsonResponse({'error': "Aucun compte n'est associé au matricule de ce reçu. "
                                      "Inscrivez-vous d'abord."}, status=400)
    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.is_admin or user.is_staff or user.is_superuser:
        return JsonResponse({'error': 'Ce compte ne peut pas se connecter avec un reçu.'}, status=403)
    if profile.has_active_session:
        return JsonResponse({
            'success': False,
            'error': "Compte déjà connecté sur un autre appareil. Déconnectez-vous d'abord ou attendez que la session expire."
        }, status=400)

    # 4) connexion
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    _open_session(request, user, profile, method='qr')
    return JsonResponse({
        'success': True,
        'user': user_to_dict(user),
        'message': 'Connexion réussie',
        'login_method': 'qr',
    })

login_required # Deconnection d'un utilisateur
def logout_view(request):
    if request.user.is_authenticated:
        try:
            profile = Profile.objects.get(user=request.user)
            profile.invalidate_session()
        except Profile.DoesNotExist:
            pass

        # Déconnecter Django
        #if(not is_user_admin(request.user)):
        from django.contrib.auth import logout
        logout(request)
        # Nettoyer la session
        request.session.flush()
        
        return JsonResponse({
            'success': True,
            'message': 'Déconnexion réussie'
        })

@csrf_exempt
@login_required  # Changer son mot de passe (ancien mot de passe obligatoire)
def change_password_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    try:
        data = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Requête invalide.'}, status=400)

    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''
    user = request.user

    if not user.check_password(old_password):
        return JsonResponse({'error': 'Ancien mot de passe incorrect.'}, status=400)
    if len(new_password) < 6:
        return JsonResponse({'error': 'Le nouveau mot de passe doit contenir au moins 6 caractères.'}, status=400)
    if new_password == old_password:
        return JsonResponse({'error': 'Le nouveau mot de passe doit être différent de l\'ancien.'}, status=400)
    if _is_default_password(user, new_password):
        return JsonResponse({'error': 'Choisissez un mot de passe différent de celui attribué par défaut.'}, status=400)

    user.set_password(new_password)
    user.save(update_fields=['password'])
    update_session_auth_hash(request, user)   # garde l'utilisateur connecté

    return JsonResponse({'success': 'Mot de passe modifié avec succès.'})



@login_required
def check_session_view(request):
    """Vérifie si un utilisateur est connecté et renvoie ses informations."""
    return JsonResponse(user_to_dict(request.user))

@login_required # Collecte des données à charger au demarrage de l'Application
def dashboard_data_view(request):
    """Renvoie toutes les données nécessaires pour le tableau de bord."""
    election = ElectionState.load()
    
    # Récupérer les candidats sans .values() pour avoir les objets complets
    candidates_queryset = Candidate.objects.all()
    
    # Sérialiser manuellement les candidats
    candidates = []
    for candidate in candidates_queryset:
        candidate_data = {
            'id': candidate.id,
            'nom': candidate.nom,
            'prenom': candidate.prenom,
            'cycle': candidate.cycle,
            'specialite': candidate.specialite,
            'niveau': candidate.niveau,
            'campus': candidate.campus,
            'slogan': candidate.slogan,
            'votes': candidate.votes if (is_user_admin(request.user) or (election.status == 'closed' and election.results_visible)) else 0,
            'bureau_color': candidate.bureau_color,
            'bureau_name': candidate.bureau_name,
            'photo_url': candidate.photo_url.url if candidate.photo_url else None,  # Convertir Cloudinary en URL string
            'programme_url': candidate.programme_url
        }
        
        # Ajouter les libellés
        candidate_data['cycle_display'] = candidate.get_cycle_display()
        candidate_data['specialite_display'] = candidate.specialite_display
        
        candidates.append(candidate_data)
    candidates.reverse()  # Pour afficher les plus récents en premier
    # Pour l'admin, on renvoie aussi les listes d'utilisateurs
    pending_users = []
    all_users = []
    if is_user_admin(request.user):
        pending_users = [user_to_dict(u) for u in User.objects.filter(profile__status='pending').order_by('first_name', 'last_name')]
        all_users = [user_to_dict(u) for u in User.objects.filter(profile__is_admin=False).order_by('first_name', 'last_name')]

    return JsonResponse({
        'user': user_to_dict(request.user),
        'election_status': election.status,
        'results_visible': election.results_visible,   # résultats publiés aux étudiants ?
        'password_login_enabled': election.password_login_enabled,   # connexion matricule + mot de passe ouverte ?
        'candidates': candidates,
        'pending_users': pending_users,
        'all_users': all_users,
    })

@csrf_exempt
@login_required # Processus d'enregistrement d'un vote
def vote_view(request):
    if request.method == 'POST':
        user_profile = request.user.profile
        election = ElectionState.load()

        if user_profile.has_voted:
            return JsonResponse({'error': 'Vous avez déjà voté.'}, status=403)
        if user_profile.status != 'validated':
            return JsonResponse({'error': 'Votre compte n\'est pas validé.'}, status=403)
        if election.status != 'active':
            return JsonResponse({'error': 'L\'élection n\'est pas active.'}, status=403)

        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')

        try:
            with transaction.atomic():
                candidate = Candidate.objects.get(id=candidate_id)
                Vote.objects.create(profile=user_profile, candidate=candidate)
                Profile.objects.filter(pk=user_profile.pk).update(has_voted=True)
                Candidate.objects.filter(pk=candidate.pk).update(
                    votes=Vote.objects.filter(candidate=candidate).count())

            return JsonResponse({'success': 'Vote enregistré !'})
        except Candidate.DoesNotExist:
            return JsonResponse({'error': 'Candidat non trouvé.'}, status=404)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

# ===============================================
# VUES API - ADMINISTRATION
# ===============================================
@csrf_exempt
@login_required  # Modifier le statut d'un etudiant et le supprimer aussi
def manage_user_status_view(request, user_id):
    if not is_user_admin(request.user):
        return JsonResponse({'error': 'Accès refusé.'}, status=403)
    
    try:
        user_to_manage = User.objects.get(id=user_id)
        profile_to_manage = user_to_manage.profile
    except User.DoesNotExist:
        return JsonResponse({'error': 'Utilisateur non trouvé.'}, status=404)

    if request.method == 'PUT': # Valider/Désactiver
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status in ['validated', 'pending']:
            profile_to_manage.status = new_status
            if new_status == 'validated':
                profile_to_manage.verification_source = 'admin'
                profile_to_manage.verified_at = timezone.now()
            profile_to_manage.save()
            return JsonResponse(user_to_dict(user_to_manage))
        return JsonResponse({'error': 'Statut invalide.'}, status=400)
    
    if request.method == 'DELETE': # Supprimer
        user_to_manage.delete()
        profile_to_manage.delete()
        return JsonResponse({'success': 'Utilisateur supprimé.'})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
@login_required  # Actions groupées : valider / désactiver / supprimer plusieurs étudiants
def bulk_users_view(request):
    if not is_user_admin(request.user):
        return JsonResponse({'error': 'Accès refusé.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    try:
        data = json.loads(request.body)
        ids = [int(i) for i in data.get('ids', [])]
    except (TypeError, ValueError, AttributeError):
        return JsonResponse({'error': 'Requête invalide.'}, status=400)
    action = data.get('action')
    if action not in ('validate', 'deactivate', 'delete'):
        return JsonResponse({'error': 'Action invalide.'}, status=400)
    if not ids:
        return JsonResponse({'error': 'Aucun étudiant sélectionné.'}, status=400)
    if len(ids) > 5000:
        return JsonResponse({'error': 'Sélection trop grande (5000 maximum).'}, status=400)

    # jamais un administrateur, jamais soi-même
    users = User.objects.filter(id__in=ids, profile__is_admin=False).exclude(id=request.user.id)
    profiles = Profile.objects.filter(user__in=users)
    skipped_voted = 0

    with transaction.atomic():
        if action == 'validate':
            done = profiles.filter(status='pending').update(
                status='validated', verification_source='admin', verified_at=timezone.now())
        elif action == 'deactivate':
            done = profiles.filter(status='validated').update(status='pending')
        else:
            # on ne supprime pas un étudiant qui a voté : son vote est déjà compté dans les résultats
            skipped_voted = profiles.filter(has_voted=True).count()
            deletable = users.filter(profile__has_voted=False)
            done = deletable.count()
            deletable.delete()

    return JsonResponse({'success': True, 'action': action, 'done': done,
                         'skipped_voted': skipped_voted, 'ignored': len(ids) - done - skipped_voted})


@login_required  # Creation d'un nouveau candidat
def manage_candidates_view(request):
    print("manage_candidates_view")
    if not is_user_admin(request.user):
        return JsonResponse({'error': 'Accès refusé.'}, status=403)
    if request.method == 'POST':
        if request.content_type == 'multipart/form-data':
                # Traitement pour FormData (avec photo)
                nom = request.POST.get('nom')
                prenom = request.POST.get('prenom')
                cycle = request.POST.get('cycle')
                specialite = request.POST.get('specialite')
                niveau = request.POST.get('niveau')
                campus = request.POST.get('campus')
                slogan = request.POST.get('slogan')
                photo = request.FILES.get('photo')
                programmePDF = request.FILES.get('programmePDF')
                bureau_nom=request.POST.get('bureau_name')
                bureau_color=request.POST.get('bureau_color', '#3498db')
                
                # Valider les données obligatoires
                if not all([nom, prenom, cycle, specialite, niveau, slogan]):
                    return JsonResponse({'error': 'Tous les champs sont obligatoires.'}, status=400)
                
                # Créer le nom complet
                name = f"{prenom} {nom}"

                # Vérifier si le candidat existe déjà
                if Candidate.objects.filter(name=name).exists():
                    return JsonResponse({'error': 'Ce candidat existe déjà.'}, status=400)
                # Créer le candidat
                candidate = Candidate.objects.create(
                    nom=nom,
                    prenom=prenom,
                    name=name,
                    cycle=cycle,
                    specialite=specialite,
                    niveau=niveau,
                    campus=campus,
                    slogan=slogan,
                    photo_url = photo,
                    bureau_name=bureau_nom,
                    bureau_color=bureau_color,
                    programme_pdf=programmePDF,
                    
                )

                
        return JsonResponse({'success': 'Inscription réussie ! Votre compte est en attente de validation.'})
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
@login_required  # Suppression d'un nouveau candidat
def manage_candidate_detail_view(request, candidate_id):
    if not is_user_admin(request.user):
        return JsonResponse({'error': 'Accès refusé.'}, status=403)
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return JsonResponse({'error': 'Candidat non trouvé.'}, status=404)

    if request.method == 'DELETE':
        candidate.delete()
        return JsonResponse({'success': 'Candidat supprimé.'})

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
@login_required # Activer ou desactiver l'election
def manage_election_view(request):
    if not is_user_admin(request.user):
        return JsonResponse({'error': 'Accès refusé.'}, status=403)
    
    if request.method == 'PUT':
        data = json.loads(request.body)
        election = ElectionState.load()

        # Montrer / cacher les résultats aux étudiants (sans toucher au statut de l'élection)
        if 'results_visible' in data:
            election.results_visible = bool(data.get('results_visible'))
            election.save(update_fields=['results_visible'])
            return JsonResponse({'status': election.status, 'results_visible': election.results_visible})

        # Activer / désactiver la connexion par matricule + mot de passe des étudiants
        # (update() et non save() : save() remet les votes à zéro quand l'élection est « pending »)
        if 'password_login_enabled' in data:
            ElectionState.objects.filter(pk=election.pk).update(
                password_login_enabled=bool(data.get('password_login_enabled')))
            return JsonResponse({'status': election.status,
                                 'password_login_enabled': bool(data.get('password_login_enabled'))})

        new_status = data.get('status')
        if new_status in ['pending', 'active', 'closed']:
            election.status = new_status
            if new_status != 'closed':
                election.results_visible = False      # on repart masqué à chaque nouvelle élection
            election.save()
            return JsonResponse({'status': election.status, 'results_visible': election.results_visible})
        return JsonResponse({'error': 'Statut invalide.'}, status=400)
        
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
@login_required  # Réinitialisation de l'élection
def reset_election_view(request):
    if not is_user_admin(request.user):
        return JsonResponse({'error': 'Accès refusé.'}, status=403)
    
    if request.method == 'POST':
        try:
            # Réinitialiser tous les votes
            Candidate.objects.all().update(votes=0)
            
            # Réinitialiser le statut "a voté" pour tous les utilisateurs
            Profile.objects.all().update(has_voted=False)

            Vote.objects.all().delete()
            
            # Remettre l'élection en statut "pending"
            election = ElectionState.objects.first()
            election.status = 'pending'
            election.results_visible = False
            election.save()
            
            return JsonResponse({'success': 'Élection réinitialisée avec succès'})
            
        except Exception as e:
            return JsonResponse({'error': f'Erreur lors de la réinitialisation: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


