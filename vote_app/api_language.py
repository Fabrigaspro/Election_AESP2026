"""Traduction FR -> EN des messages renvoyés par l'API.

Le navigateur envoie le cookie `lang` (fr ou en). Quand il vaut "en", ce middleware
traduit les champs error / message / success / reasons / detail des réponses JSON de /api/.
Les vues et receipt_verifier.py restent inchangés (ils écrivent toujours en français).
Un message absent du dictionnaire reste en français : il suffit de l'ajouter dans EXACT.
"""
import json
import re

EXACT = {
    # --- Général ---
    "Cycle non spécifié": "Cycle not specified",
    "Méthode non autorisée": "Method not allowed",
    "Accès refusé.": "Access denied.",
    "Statut invalide.": "Invalid status.",
    # --- Inscription ---
    "Matricule manquant.": "Student ID is missing.",
    "Nom et prénom obligatoires.": "Last name and first name are required.",
    "Mot de passe manquant.": "Password is missing.",
    "Ce matricule est déjà utilisé.": "This student ID is already in use.",
    "La photo de profil est obligatoire.": "A profile photo is required.",
    "Le reçu est obligatoire.": "The receipt is required.",
    "Trop de tentatives. Réessayez dans une heure.": "Too many attempts. Please try again in an hour.",
    "Ce reçu a déjà été utilisé pour une autre inscription. Si c'est une erreur, contactez l'administrateur.":
        "This receipt has already been used for another registration. If this is a mistake, please contact the administrator.",
    "Erreur base de données lors de la création du compte.": "Database error while creating the account.",
    "Problème lors de la création du profil. Connexion instable":
        "Problem while creating the profile. Unstable connection.",
    "Inscription validée automatiquement.": "Registration automatically approved.",
    "Votre reçu a été vérifié : votre compte est validé. Vous pouvez maintenant vous connecter.":
        "Your receipt has been verified: your account is approved. You can now log in.",
    "Inscription enregistrée, en attente de vérification.": "Registration saved, pending verification.",
    "Votre inscription est enregistrée, mais votre reçu n'a pas pu être confirmé automatiquement. Un administrateur va le vérifier.":
        "Your registration is saved, but your receipt could not be confirmed automatically. An administrator will check it.",
    "Votre inscription est enregistrée, mais l'analyse automatique du reçu est momentanément indisponible. Un administrateur va le vérifier.":
        "Your registration is saved, but the automatic receipt analysis is temporarily unavailable. An administrator will check it.",
    "Inscription refusée : votre reçu ne correspond pas aux informations saisies. Corrigez les points ci-dessous puis réessayez.":
        "Registration refused: your receipt does not match the information entered. Please fix the points below and try again.",
    "Inscription réussie ! Votre compte est en attente de validation.":
        "Registration successful! Your account is awaiting validation.",
    "Type de fichier non autorisé (seuls jpg, jpeg et png sont autorisés).":
        "File type not allowed (only jpg, jpeg and png are accepted).",
    "Nom de fichier sans extension.": "File name has no extension.",
    "Le fichier du reçu n'est pas une image valide.": "The receipt file is not a valid image.",
    "Le fichier du reçu est vide.": "The receipt file is empty.",
    "Le reçu dépasse la taille maximale autorisée (8 Mo).": "The receipt exceeds the maximum allowed size (8 MB).",
    # --- Connexion ---
    "Compte déjà connecté sur un autre appareil. Déconnectez-vous d'abord ou attendez que la session expire.":
        "Account already logged in on another device. Log out there first or wait for the session to expire.",
    "Connexion réussie": "Login successful",
    "Matricule ou mot de passe incorrect": "Incorrect student ID or password",
    "Déconnexion réussie": "Logout successful",
    # --- Vote et administration ---
    "Vous avez déjà voté.": "You have already voted.",
    "Votre compte n'est pas validé.": "Your account is not approved.",
    "L'élection n'est pas active.": "The election is not active.",
    "Vote enregistré !": "Vote recorded!",
    "Candidat non trouvé.": "Candidate not found.",
    "Utilisateur non trouvé.": "User not found.",
    "Utilisateur supprimé.": "User deleted.",
    "Tous les champs sont obligatoires.": "All fields are required.",
    "Ce candidat existe déjà.": "This candidate already exists.",
    "Candidat supprimé.": "Candidate deleted.",
    "Élection réinitialisée avec succès": "Election reset successfully",
    # --- Contrôles du reçu (receipt_verifier.py) ---
    "Analyse automatique indisponible : vérification manuelle requise":
        "Automatic analysis unavailable: manual verification required",
    "L'image est un reçu de paiement": "The image is a payment receipt",
    "L'image ne semble pas être un reçu de paiement": "The image does not look like a payment receipt",
    "Reçu lisible": "Receipt is legible",
    "Reçu peu lisible (photo floue, coupée ou trop sombre)": "Receipt is hard to read (blurry, cropped or too dark photo)",
    "Matricule conforme au reçu": "Student ID matches the receipt",
    "Matricule introuvable sur le reçu": "Student ID not found on the receipt",
    "Le matricule saisi ne correspond pas à celui du reçu": "The student ID entered does not match the one on the receipt",
    "Nom introuvable sur le reçu": "Name not found on the receipt",
    "Année académique non indiquée sur le reçu": "Academic year not shown on the receipt",
    "École non indiquée sur le reçu": "School not shown on the receipt",
    "QR code illisible : matricule introuvable": "QR code unreadable: student ID not found",
    "Matricule du QR code conforme au matricule saisi": "QR code student ID matches the one entered",
    "Le matricule du QR code ne correspond pas au matricule saisi": "The QR code student ID does not match the one entered",
    "Matricule du QR code conforme au matricule imprimé": "QR code student ID matches the printed one",
    "Le matricule du QR code diffère de celui imprimé sur le reçu": "The QR code student ID differs from the one printed on the receipt",
    "QR code : année académique introuvable": "QR code: academic year not found",
    "Année du QR code conforme à l'année imprimée": "QR code year matches the printed year",
    "QR code du reçu introuvable ou illisible": "Receipt QR code not found or unreadable",
    "QR code du reçu introuvable ou illisible : refaites une photo nette, avec le QR code bien visible et sans reflet":
        "Receipt QR code not found or unreadable: retake a sharp photo with the QR code clearly visible and no glare",
    "Niveau conforme au reçu": "Level matches the receipt",
    "Le niveau choisi ne correspond pas à celui du reçu": "The level selected does not match the one on the receipt",
    "Campus conforme au reçu": "Campus matches the receipt",
    "Le campus choisi ne correspond pas à celui du reçu": "The campus selected does not match the one on the receipt",
}

# (expression régulière, fonction qui construit la phrase anglaise à partir du résultat)
PATTERNS = [
    (r"^Photo invalide: (.+)$", lambda m: "Invalid photo: " + translate(m.group(1))),
    (r"^Reçu invalide: (.+)$", lambda m: "Invalid receipt: " + translate(m.group(1))),
    (r"^Fichier trop volumineux \(>(.+) MB\)\.$", lambda m: f"File too large (>{m.group(1)} MB)."),
    (r"^Extension non autorisée: (.+)$", lambda m: f"Extension not allowed: {m.group(1)}"),
    (r"^Erreur de connexion: (.+)$", lambda m: f"Login error: {m.group(1)}"),
    (r"^Erreur lors de la réinitialisation: (.+)$", lambda m: f"Error while resetting: {m.group(1)}"),
    (r"^Nom conforme au reçu \((.+)\)$", lambda m: f"Name matches the receipt ({m.group(1)})"),
    (r"^Le nom saisi ne correspond pas à celui du reçu \((.+)\)$",
     lambda m: f"The name entered does not match the one on the receipt ({m.group(1)})"),
    (r"^Année académique conforme \((.+)\)$", lambda m: f"Academic year matches ({m.group(1)})"),
    (r"^Reçu d'une autre année académique \((.+), attendue (.+)\)$",
     lambda m: f"Receipt from a different academic year ({m.group(1)}, expected {m.group(2)})"),
    (r"^École conforme \((.+)\)$", lambda m: f"School matches ({m.group(1)})"),
    (r"^Reçu d'une autre école \((.+), attendue (.+)\)$",
     lambda m: f"Receipt from a different school ({m.group(1)}, expected {m.group(2)})"),
    (r"^Année du QR code conforme \((.+)\)$", lambda m: f"QR code year matches ({m.group(1)})"),
    (r"^Le QR code indique une autre année académique \((.+), attendue (.+)\)$",
     lambda m: f"The QR code shows a different academic year ({m.group(1)}, expected {m.group(2)})"),
    (r"^L'année du QR code \((.+)\) diffère de l'année imprimée \((.+)\)$",
     lambda m: f"The QR code year ({m.group(1)}) differs from the printed year ({m.group(2)})"),
    (r"^Points suspects relevés : (.+)$", lambda m: f"Suspicious points noted: {m.group(1)}"),
]
_COMPILED = [(re.compile(p, re.S), f) for p, f in PATTERNS]

FIELDS = ("error", "message", "success", "detail", "reasons")


def translate(text):
    """Traduit une phrase française en anglais ; renvoie le texte tel quel s'il est inconnu."""
    if not isinstance(text, str):
        return text
    s = text.strip()
    if s in EXACT:
        return EXACT[s]
    for rx, build in _COMPILED:
        m = rx.match(s)
        if m:
            return build(m)
    return text


def _translate_value(value):
    if isinstance(value, str):
        return translate(value)
    if isinstance(value, list):
        return [_translate_value(v) for v in value]
    return value


class ApiLanguageMiddleware:
    """À placer après CommonMiddleware dans MIDDLEWARE."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.COOKIES.get("lang") != "en" or not request.path.startswith("/api/"):
            return response
        if "application/json" not in (response.get("Content-Type") or ""):
            return response
        try:
            data = json.loads(response.content)
        except (ValueError, TypeError):
            return response
        if not isinstance(data, dict):
            return response
        for key in FIELDS:
            if key in data:
                data[key] = _translate_value(data[key])
        response.content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        return response
