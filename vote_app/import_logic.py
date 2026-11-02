"""Lecture et normalisation de la liste officielle des étudiants (fichier ETUDIANTS_SP).

Aucune dépendance Django : ce module ne fait que lire le fichier et préparer les données.
Les correspondances Excel -> codes de l'application sont dans les dictionnaires ci-dessous :
modifiez-les ici si une spécialité n'est pas rangée comme vous le souhaitez.
"""
import csv
import os
import re
import secrets

# --------------------------------------------------------------------------------------
# Correspondances Excel -> application
# --------------------------------------------------------------------------------------
CAMPUS_MAP = {
    "BONAMOUSSADI A": "Bonamoussadi A",
    "BONABERI A": "Bonaberi",
}

CYCLE_MAP = {
    "BTS": "bts",
    "INDUSTRIAL HND": "hnd",
    "BACHELOR OF TECHNOLOGY": "bachelor",
    "LICENCE": "lipro",                       # le fichier ne distingue pas Licence Pro / Licence Tech
    "MASTER": "master",
    "MASTERS OF TECHNOLOGY": "master",
    "INGENIEUR": "ingenieur",
    "ENGINEERING CYCLE": "ingenieur",
    "CLASSES PREPARATOIRES INGENIEURS": "ingenieur",
    "CLASSES PREPARATOIRES ANNECY CHAMBERY": "ingenieur",
}
PREPA_CYCLES = {"CLASSES PREPARATOIRES INGENIEURS", "CLASSES PREPARATOIRES ANNECY CHAMBERY"}
CYCLES_AMBIGUS = {"LICENCE"}

SPEC_MAP = {
    "bts": {"GL A": "GL", "GL B": "GL", "GL": "GL", "RS": "RES", "BAT": "BAT", "CHAU": "CHAU",
            "MCA": "MECATRO", "ET": "ET", "TOPO": "GTO", "IIA": "IIA", "IWD": "IWD", "ECOM": "ECOM",
            "TPU": "TP", "TEL": "TELECOM", "TELECOM": "TELECOM"},
    "hnd": {"SWE A": "SWE", "SWE B": "SWE", "SWE": "SWE", "NWS": "NWSE", "CGWD": "CGWD",
            "BST": "BST", "ETC": "ECT", "TOPO": "TOPO", "EPS": "EPS"},
    "lipro": {"ASR": "ASR", "GL": "GL", "QHSE": "QHSE", "SIR": "SIR", "GEII": "GEII", "BAT": "BAT",
              "TELECOM": "TELECOM", "TPU": "TP", "TP": "TP"},
    "bachelor": {"SWE": "SWE", "CNSM": "CNSM", "CE": "CE", "3E": "EEE"},
    "master": {"ASR": "ASR", "GL": "GL", "QHSE": "QHSE", "SIR": "SIR", "GEII": "GEII"},
    "ingenieur": {"GC": "GCE", "GIT": "GIT", "GESI": "GESI", "GM": "GM", "GAM": "GMA",
                  "GMA": "GMA", "GE": "GESI", "GMP": "GM"},
}
# Correspondances plausibles mais non certaines : signalées dans le rapport « à vérifier »
INCERTAINES = {("bts", "MCA"), ("bts", "TPU"), ("lipro", "TPU"), ("bachelor", "3E"),
               ("ingenieur", "GAM"), ("ingenieur", "GE"), ("ingenieur", "GMP")}

MATRICULE_STANDARD = re.compile(r"^\d{2}IU\d{5}$")
COLONNES_OBLIGATOIRES = ["Matricules", "Nom_Etudiant", "Prenom_Etudiant", "Nom_Cycle", "Code_Specialite",
                         "Nom_Niveau", "Nom_Campus", "Nom_Periode", "Sexe", "Telephone"]


# --------------------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------------------
def nettoyer(valeur):
    """Texte propre : sans espaces superflus, jamais None."""
    return re.sub(r"\s+", " ", str(valeur if valeur is not None else "")).strip()


def normaliser_matricule(valeur):
    return re.sub(r"\s+", "", str(valeur or "")).upper()


def normaliser_telephone(valeur):
    """Renvoie un numéro à 9 chiffres plausible, sinon '' (zéros, numéros trop courts, etc.)."""
    chiffres = re.sub(r"\D", "", str(valeur or ""))
    if len(chiffres) == 12 and chiffres.startswith("237"):
        chiffres = chiffres[3:]
    if len(chiffres) == 9 and chiffres[0] in "62" and len(set(chiffres)) > 2:
        return chiffres
    return ""


def generer_mot_de_passe(nom, prenom, longueur=None):
    """Mot de passe = 2 premières lettres de chaque mot du nom,
    suivies des 2 premières lettres de chaque mot du prénom.

    Exemples :
        NGUEFACK KENFACK / ERICA DANY  -> 'NGKEERDA'
        MARIMAR BRIGETTE / ABONG NJI   -> 'MABRABNJ'
        NJOYA / FAHID JAIRO            -> 'NJFAJA'
        NJOYA / FAHID                  -> 'NJFA'
        CHRISTIAN ARISTIDE DE FOLLY / . -> 'CHARDEFO'   (prénom vide)
    """
    def deux_lettres_par_mot(champ):
        """Découpe le champ en mots alphabétiques et prend 2 lettres de chaque."""
        # Remplace tout caractère non alphabétique par un espace, puis découpe
        nettoye = "".join(c if c.isalpha() else " " for c in (champ or ""))
        mots = [m for m in nettoye.split() if m]
        return "".join(mot[:2].upper() for mot in mots)

    mdp = deux_lettres_par_mot(nom) + deux_lettres_par_mot(prenom)

    # Sécurité : si le résultat est vide (cas pathologique), génère un fallback
    if not mdp:
        import secrets
        mdp = "".join(secrets.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(8))

    return mdp
# --------------------------------------------------------------------------------------
# Lecture du fichier (CSV, ou Excel .xls / .xlsx si pandas est installé)
# --------------------------------------------------------------------------------------
def lire_lignes(chemin):
    extension = os.path.splitext(chemin)[1].lower()
    if extension in (".xls", ".xlsx"):
        try:
            import pandas as pd
            tableau = pd.read_excel(chemin, dtype=str).fillna("")
        except ImportError as exc:
            raise RuntimeError(
                "Lecture Excel impossible : installez 'pandas' et 'xlrd' (pip install pandas xlrd), "
                "ou enregistrez le fichier au format CSV UTF-8 depuis Excel."
            ) from exc
        lignes = tableau.to_dict("records")
    else:
        contenu = None
        for encodage in ("utf-8-sig", "cp1252"):
            try:
                with open(chemin, encoding=encodage, newline="") as f:
                    contenu = f.read()
                break
            except UnicodeDecodeError:
                continue
        if contenu is None:
            raise RuntimeError("Encodage du fichier CSV non reconnu.")
        separateur = ";" if contenu.split("\n", 1)[0].count(";") > contenu.split("\n", 1)[0].count(",") else ","
        lignes = list(csv.DictReader(contenu.splitlines(), delimiter=separateur))

    # En-têtes sans espaces
    lignes = [{nettoyer(k): v for k, v in ligne.items()} for ligne in lignes]
    manquantes = [c for c in COLONNES_OBLIGATOIRES if lignes and c not in lignes[0]]
    if manquantes:
        raise RuntimeError("Colonnes introuvables dans le fichier : " + ", ".join(manquantes))
    return lignes


# --------------------------------------------------------------------------------------
# Normalisation d'une ligne
# --------------------------------------------------------------------------------------
def normaliser_ligne(brut):
    """Transforme une ligne du fichier en dictionnaire propre.

    Renvoie (donnees, erreur). `donnees` est None si la ligne est inutilisable.
    Gère les lignes de Bonabéri, décalées d'une colonne dans le fichier d'origine :
    matricule dans « Nom_Periode », nom dans « Matricules », prénom dans « Nom_Etudiant »,
    téléphone dans « Sexe ».
    """
    g = {k: nettoyer(v) for k, v in brut.items()}
    decalee = g["Nom_Periode"] not in ("FI", "FC") and g["Nom_Periode"] != ""
    if decalee:
        matricule, nom, prenom, tel_brut = g["Nom_Periode"], g["Matricules"], g["Nom_Etudiant"], g["Sexe"]
    else:
        matricule, nom, prenom, tel_brut = g["Matricules"], g["Nom_Etudiant"], g["Prenom_Etudiant"], g["Telephone"]

    matricule = normaliser_matricule(matricule)
    if not matricule:
        return None, "matricule vide"
    if not nom:
        return None, "nom vide"

    cycle_excel = g["Nom_Cycle"].upper()
    cycle = CYCLE_MAP.get(cycle_excel)
    if not cycle:
        return None, f"cycle inconnu : {g['Nom_Cycle']}"

    campus = CAMPUS_MAP.get(g["Nom_Campus"].upper())
    if not campus:
        return None, f"campus inconnu : {g['Nom_Campus']}"

    try:
        niveau = int(float(g["Nom_Niveau"]))
    except ValueError:
        return None, f"niveau invalide : {g['Nom_Niveau']}"

    code = g["Code_Specialite"].upper()
    drapeaux = []
    if cycle_excel in PREPA_CYCLES:
        specialite = "Prépa"
    else:
        specialite = SPEC_MAP.get(cycle, {}).get(code)
        if specialite is None:
            specialite = code                       # code conservé tel quel, à vérifier
            drapeaux.append("spécialité non reconnue : " + (code or "vide"))
        elif (cycle, code) in INCERTAINES:
            drapeaux.append(f"spécialité à vérifier : {code} -> {specialite}")

    if cycle_excel in CYCLES_AMBIGUS:
        drapeaux.append("cycle « LICENCE » rangé en Licence Pro (Pro ou Tech ?)")
    if not MATRICULE_STANDARD.match(matricule):
        drapeaux.append("matricule atypique")
    telephone = normaliser_telephone(tel_brut)
    if not telephone:
        drapeaux.append("téléphone absent ou invalide")

    return {
        "matricule": matricule, "nom": nom, "prenom": prenom, "telephone": telephone,
        "campus": campus, "cycle": cycle, "specialite": specialite, "niveau": niveau,
        "drapeaux": drapeaux,
    }, None


def charger_liste(chemin):
    """Lit tout le fichier. Renvoie (etudiants, erreurs, doublons)."""
    etudiants, erreurs, doublons, vus = [], [], [], set()
    for numero, brut in enumerate(lire_lignes(chemin), start=2):          # ligne 1 = en-têtes
        donnees, erreur = normaliser_ligne(brut)
        if erreur:
            erreurs.append((numero, erreur))
        elif donnees["matricule"] in vus:
            doublons.append((numero, donnees["matricule"]))
        else:
            vus.add(donnees["matricule"])
            etudiants.append(donnees)
    return etudiants, erreurs, doublons
