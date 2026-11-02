"""Crée les comptes des étudiants à partir de la liste officielle (ETUDIANTS_SP).

Étapes conseillées :
  1) Simulation (rien n'est écrit en base) :
       python manage.py import_etudiants ETUDIANTS_SP.xls
  2) Création réelle :
       python manage.py import_etudiants ETUDIANTS_SP.xls --appliquer

Les comptes déjà existants (même matricule, majuscules ou minuscules) ne sont jamais modifiés,
sauf avec --maj-existants qui corrige uniquement campus, cycle, spécialité et niveau.
"""
import csv
import os
from datetime import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from vote_app import import_logic as logic
from vote_app.models import Profile

CHAMPS_PROFIL = ("campus", "cycle", "specialite", "niveau")


class Command(BaseCommand):
    help = "Crée les comptes étudiants à partir du fichier officiel (simulation par défaut)."

    def add_arguments(self, parser):
        parser.add_argument("fichier", help="Fichier .xls, .xlsx ou .csv de la liste officielle")
        parser.add_argument("--appliquer", action="store_true", help="Écrit réellement en base (sinon simulation)")
        parser.add_argument("--maj-existants", action="store_true",
                            help="Corrige campus/cycle/spécialité/niveau des comptes déjà créés")
        parser.add_argument("--limite", type=int, default=0, help="Ne traite que les N premiers étudiants (test)")
        parser.add_argument("--sortie", default=os.path.expanduser("~/import_etudiants"),
                            help="Dossier des fichiers de rapport (hors du projet !)")

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        appliquer = options["appliquer"]
        try:
            etudiants, erreurs, doublons = logic.charger_liste(options["fichier"])
        except (OSError, RuntimeError) as exc:
            raise CommandError(str(exc))
        if options["limite"]:
            etudiants = etudiants[: options["limite"]]

        dossier = options["sortie"]
        os.makedirs(dossier, exist_ok=True)
        horodatage = datetime.now().strftime("%Y%m%d_%H%M")

        # Comptes existants, comparés sans tenir compte de la casse
        existants = {u.username.upper(): u for u in User.objects.select_related("profile")}
        matricules_liste = {e["matricule"] for e in etudiants}

        crees, deja, corriges = [], 0, 0
        a_verifier, differences, echecs = [], [], []

        for i, e in enumerate(etudiants, start=1):
            if e["drapeaux"]:
                a_verifier.append(e)
            user = existants.get(e["matricule"])
            if user is not None:                                   # compte déjà présent : on le préserve
                deja += 1
                profil = getattr(user, "profile", None)
                if profil is not None and not profil.is_admin:
                    diff = [c for c in CHAMPS_PROFIL if str(getattr(profil, c) or "") != str(e[c])]
                    if diff:
                        differences.append((e, diff))
                        if appliquer and options["maj_existants"]:
                            for c in diff:
                                setattr(profil, c, e[c])
                            profil.save()
                            corriges += 1
                continue

            mot_de_passe = logic.generer_mot_de_passe(e["nom"], e["prenom"])
            if appliquer:
                try:
                    with transaction.atomic():
                        user = User(username=e["matricule"], first_name=e["nom"], last_name=e["prenom"])
                        user.set_password(mot_de_passe)
                        user.save()
                        Profile.objects.create(
                            user=user, campus=e["campus"], cycle=e["cycle"], specialite=e["specialite"],
                            niveau=e["niveau"], telephone=e["telephone"], photo="", recu="",
                            role="student", status="validated", verification_source="import",
                            verification_score=1.0,
                            verification_note="Compte créé à partir de la liste officielle des étudiants.",
                            verified_at=timezone.now(),
                        )
                    existants[e["matricule"]] = user
                except Exception as exc:                            # un échec n'arrête pas l'import
                    echecs.append((e["matricule"], str(exc)[:120]))
                    continue
            crees.append((e, mot_de_passe))
            if appliquer and len(crees) % 100 == 0:
                self.stdout.write(f"  ... {len(crees)} comptes créés")

        # Comptes existants absents de la liste officielle (à examiner, jamais supprimés)
        hors_liste = [u for key, u in existants.items()
                      if key not in matricules_liste and hasattr(u, "profile")
                      and not u.profile.is_admin and not u.is_staff]

        # ---------------- fichiers de rapport ----------------
        def ecrire(nom, entetes, lignes, secret=False):
            chemin = os.path.join(dossier, f"{nom}_{horodatage}.csv")
            with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(entetes)
                w.writerows(lignes)
            if secret:
                os.chmod(chemin, 0o600)
            return chemin

        fichiers = []
        if appliquer and crees:
            fichiers.append(ecrire("identifiants", ["matricule", "nom", "prenom", "telephone", "mot_de_passe"],
                                   [[e["matricule"], e["nom"], e["prenom"], e["telephone"], mdp] for e, mdp in crees],
                                   secret=True))
        if a_verifier:
            fichiers.append(ecrire("a_verifier", ["matricule", "nom", "prenom", "points a verifier"],
                                   [[e["matricule"], e["nom"], e["prenom"], " | ".join(e["drapeaux"])]
                                    for e in a_verifier]))
        if hors_liste:
            fichiers.append(ecrire("comptes_hors_liste", ["matricule", "nom", "prenom", "statut", "a_vote"],
                                   [[u.username, u.first_name, u.last_name, u.profile.status, u.profile.has_voted]
                                    for u in hors_liste]))
        if differences:
            fichiers.append(ecrire("differences", ["matricule", "champs differents"],
                                   [[e["matricule"], ", ".join(d)] for e, d in differences]))

        # ---------------- résumé ----------------
        out = self.stdout.write
        out("")
        out(self.style.WARNING("SIMULATION : rien n'a été écrit en base." if not appliquer else "IMPORT TERMINÉ."))
        out(f"  Étudiants lus dans le fichier ........ {len(etudiants)}")
        out(f"  Comptes {'créés' if appliquer else 'à créer'} ................. {len(crees)}")
        out(f"  Comptes déjà existants (préservés) ... {deja}")
        if options["maj_existants"] and appliquer:
            out(f"  Comptes existants corrigés ........... {corriges}")
        out(f"  Existants avec infos différentes ..... {len(differences)}")
        out(f"  Existants ABSENTS de la liste ........ {len(hors_liste)}   (à examiner, rien n'est supprimé)")
        out(f"  Lignes à vérifier (signalées) ........ {len(a_verifier)}")
        out(f"  Lignes ignorées (données invalides) .. {len(erreurs)}")
        out(f"  Doublons dans le fichier ignorés ..... {len(doublons)}")
        if echecs:
            out(self.style.ERROR(f"  ÉCHECS de création ................... {len(echecs)}"))
            for mat, msg in echecs[:10]:
                out(f"      {mat} : {msg}")
        for numero, motif in erreurs[:10]:
            out(f"      ligne {numero} ignorée : {motif}")
        if fichiers:
            out("")
            out(f"Fichiers de rapport dans : {dossier}")
            for f in fichiers:
                out("   - " + os.path.basename(f))
            out(self.style.WARNING("Ces fichiers contiennent des données personnelles : "
                                   "ne les mettez jamais dans GitHub."))
        if not appliquer:
            out("")
            out("Si ce résumé vous convient, relancez avec --appliquer.")
