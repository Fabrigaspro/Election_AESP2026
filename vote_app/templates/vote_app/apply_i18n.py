#!/usr/bin/env python3
"""Rend index.html bilingue (FR/EN).

Usage :  python apply_i18n.py chemin/vers/index.html
Crée   :  index.html.bak (sauvegarde) puis modifie index.html sur place.

Principe : le français reste la langue source. Un dictionnaire FR -> EN est injecté dans la
page ; t("texte français") renvoie l'anglais quand la langue choisie est "en". Le texte
statique du HTML est traduit au chargement, les textes écrits par le JavaScript passent par t().
Le script est rejouable : s'il détecte qu'il est déjà appliqué, il s'arrête.
"""
import json
import re
import shutil
import sys

EN = {
    # ---- Titre et chargements ----
    "Élection du Gouverneur AESP - South Polytech": "AESP Governor Election - South Polytech",
    "Chargement...": "Loading...",
    "Chargement de l'application...": "Loading the application...",
    "Connexion en cours...": "Signing in...",
    "Inscription en cours...": "Registering...",
    "Enregistrement de votre vote...": "Recording your vote...",
    "Enregistrement du candidat...": "Saving the candidate...",
    "Supression du candidat...": "Deleting the candidate...",
    "Élection du Gouverneur de l'AESP 2026/2027": "AESP Governor Election 2026/2027",
    "Association des Étudiants de South Polytech": "South Polytech Students' Association",
    # ---- Fenêtres de confirmation ----
    "✅ Inscription Réussie !": "✅ Registration Successful!",
    "Votre inscription a été enregistrée avec succès.": "Your registration has been recorded successfully.",
    "Votre compte est en attente de validation par un administrateur.": "Your account is awaiting validation by an administrator.",
    "❌ Erreur d'Inscription": "❌ Registration Error",
    "Une erreur est survenue lors de l'inscription.": "An error occurred during registration.",
    # ---- Connexion / inscription ----
    "Voir la vidéo tutorielle": "Watch the tutorial video",
    "Connexion": "Login",
    "Matricule": "Student ID",
    "Mot de passe": "Password",
    "Se connecter": "Log in",
    "Pas encore de compte ?": "No account yet?",
    "S'inscrire": "Sign up",
    "Inscription Étudiant": "Student Registration",
    "Nom": "Last name",
    "Prénom": "First name",
    "Matricule scolaire": "School student ID",
    "Cycle": "Cycle",
    "Sélectionnez votre cycle": "Select your cycle",
    "Licence Professionnelle": "Professional Bachelor's (Licence Pro)",
    "Licence de Technologie": "Technology Bachelor's (Licence Tech)",
    "Ingénieur": "Engineering",
    "Spécialité": "Specialty",
    "Sélectionnez d'abord le cycle": "Select the cycle first",
    "Sélectionnez votre spécialité": "Select your specialty",
    "Sélectionnez votre niveau": "Select your level",
    "Sélectionnez votre campus": "Select your campus",
    "Sélectionnez d'abord la specialité": "Select the specialty first",
    "Erreur de chargement": "Loading error",
    "Niveau": "Level",
    "Téléphone (Whatsapp)": "Phone (WhatsApp)",
    "Confirmer le mot de passe": "Confirm password",
    "Photo de profil": "Profile photo",
    "Photo du reçu IUGET": "IUGET receipt photo",
    "Photo nette et entière du reçu. Votre matricule, votre nom, votre cycle, votre niveau et votre campus doivent y être lisibles et identiques à ce que vous avez saisi : ils sont vérifiés automatiquement pour valider votre compte.":
        "A sharp, complete photo of the receipt. Your student ID, name, cycle, level and campus must be readable on it and identical to what you entered: they are checked automatically to approve your account.",
    "Déjà un compte ?": "Already have an account?",
    # ---- Espace étudiant ----
    "Bienvenue !": "Welcome!",
    "Votre inscription est en attente de validation par un administrateur.": "Your registration is awaiting validation by an administrator.",
    "Veuillez patienter. Vous serez notifié(e) lorsque votre compte sera activé.": "Please wait. You will be notified when your account is activated.",
    "Se déconnecter": "Log out",
    "Choisissez votre candidat préféré en cliquant sur sa carte. Vous ne pourrez voter qu'une seule fois !": "Choose your preferred candidate by clicking on their card. You can only vote once!",
    "Liste des Candidats": "List of Candidates",
    "Candidat sélectionné :": "Selected candidate:",
    "Confirmer mon vote": "Confirm my vote",
    "Votre vote a été enregistrée avec succès.": "Your vote has been recorded successfully.",
    "Les résultats seront annoncés à la fin de la période de vote.": "The results will be announced at the end of the voting period.",
    "Vous pouvez à présent consulter les resultat des votes": "You can now view the voting results",
    "Résultats de l'élection": "Election results",
    "Merci étudiant(e) {name} d'avoir voté !": "Thank you, {name}, for voting!",
    "Bienvenue, {name}": "Welcome, {name}",
    # ---- Administration ----
    "Tableau de Bord Administrateur": "Administrator Dashboard",
    "Validation des Inscriptions": "Registration Validation",
    "Gestion des Étudiants": "Student Management",
    "Gestion des Candidats": "Candidate Management",
    "Gestion de l'Élection": "Election Management",
    "Voir les Résultats": "View Results",
    "Étudiants en attente de validation": "Students awaiting validation",
    "Ajouter un candidat": "Add a candidate",
    "Nom du Bureau": "Team name",
    "Ex: Bureau du renouveau": "e.g. Renewal Team",
    "Slogan de campagne": "Campaign slogan",
    "Ex: L'avenir ensemble !": "e.g. The future together!",
    "Programme de campagne PDF": "Campaign programme (PDF)",
    "Couleur du Bureau": "Team colour",
    "Photo du candidat": "Candidate photo",
    "Ajouter le candidat": "Add the candidate",
    "Candidats actuels": "Current candidates",
    "Statut de l'élection": "Election status",
    "Statut actuel :": "Current status:",
    "Démarrer l'élection": "Start the election",
    "Terminer l'élection": "End the election",
    "Réinitialiser l'élection": "Reset the election",
    "Statistiques": "Statistics",
    "Liste des Étudiants inscrits à l'AESP": "List of students registered with the AESP",
    "© 2025 AESP - South Polytech. Tous droits réservés.": "© 2025 AESP - South Polytech. All rights reserved.",
    # ---- Recherche / filtres (liste des étudiants) ----
    "🔍 Rechercher un nom ou un matricule...": "🔍 Search by name or student ID...",
    "Tous les cycles": "All cycles",
    "Toutes les spécialités": "All specialties",
    "Vote : tous": "Vote: all",
    "✅ A voté": "✅ Has voted",
    "❌ N'a pas voté": "❌ Has not voted",
    "Réinitialiser": "Reset",
    "{n} étudiant(s) affiché(s) sur {m}": "{n} of {m} student(s) shown",
    "Aucun étudiant ne correspond à cette recherche.": "No student matches this search.",
    "Total des inscrits : {n}": "Total registered: {n}",
    "Total en attente : {n}": "Total pending: {n}",
    "Total des votes : {n}": "Total votes: {n}",
    # ---- Textes générés par le JavaScript ----
    "✅ Données mises à jour": "✅ Data updated",
    "Erreur de communication avec le serveur.": "Communication error with the server.",
    "Erreur {status}": "Error {status}",
    "Erreur : {msg}": "Error: {msg}",
    "Erreur lors du vote : {msg}": "Error while voting: {msg}",
    "❌ Erreur lors de la réinitialisation : {msg}": "❌ Error while resetting: {msg}",
    "Les mots de passe ne correspondent pas.": "Passwords do not match.",
    "L'élection n'est pas encore ouverte.": "The election is not open yet.",
    "L'élection est terminée. Voici les résultats compilés: ": "The election is over. Here are the compiled results: ",
    "Aucun candidat enregistré.": "No candidate registered.",
    "Aucun candidat n'est enregistré pour le moment.": "No candidate is registered at the moment.",
    "L'élection n'a pas encore commencé.": "The election has not started yet.",
    "L'élection est encore en cours...": "The election is still in progress...",
    "Aucun étudiant en attente de validation.": "No student awaiting validation.",
    "Aucun étudiant enregistré.": "No student registered.",
    "Voir le programme": "View the programme",
    "Voir le programme de campagne": "View campaign programme",
    "Sélectionné": "Selected",
    "Spécialité:": "Specialty:",
    "Niveau:": "Level:",
    "Bureau:": "Team:",
    "Choisir ce candidat": "Choose this candidate",
    "Voir le reçu": "View receipt",
    "Contrôle automatique du reçu": "Automatic receipt check",
    "Valider": "Approve",
    "Supprimer": "Delete",
    "Désactiver": "Deactivate",
    "Votes totaux": "Total votes",
    "Électeurs inscrits": "Registered voters",
    "Taux de participation": "Turnout",
    "Candidats": "Candidates",
    "Attention :": "Warning:",
    "La réinitialisation effacera tous les votes et remettra l'élection à zéro.": "Resetting will erase all votes and reset the election to zero.",
    "En attente": "Pending",
    "Validée": "Approved",
    " - ❌ Ne peut pas voter": " - ❌ Cannot vote",
    " - ✅ A voté": " - ✅ Has voted",
    " - ❌ N'a pas voté": " - ❌ Has not voted",
    "🟡 En attente": "🟡 Pending",
    "🔴 Terminée": "🔴 Closed",
    "Tutoriel d'utilisation": "User tutorial",
    "Tutoriel de la plateforme de vote": "Voting platform tutorial",
    "Appuyez sur Échap ou cliquez sur": "Press Esc or click",
    "pour fermer": "to close",
    # ---- Boîtes de dialogue ----
    "Veuillez sélectionner un candidat avant de voter.": "Please select a candidate before voting.",
    "Êtes-vous sûr de vouloir voter pour {name} ?\n\nCette action est irréversible et vous ne pourrez plus modifier votre choix.":
        "Are you sure you want to vote for {name}?\n\nThis action is irreversible and you will no longer be able to change your choice.",
    "Êtes-vous sûr de vouloir supprimer cet utilisateur ?": "Are you sure you want to delete this user?",
    "Êtes-vous sûr de vouloir desactiver cet étudiant ?": "Are you sure you want to deactivate this student?",
    "Vous ne pouvez pas ajouter un candidat pendant une élection active.": "You cannot add a candidate during an active election.",
    "Veuillez remplir tous les champs obligatoires.": "Please fill in all required fields.",
    "Vous ne pouvez pas supprimer un candidat pendant une élection active.": "You cannot delete a candidate during an active election.",
    "Êtes-vous sûr de vouloir supprimer ce candidat ?": "Are you sure you want to delete this candidate?",
    "Il doit y avoir au moins deux candidats pour démarrer l'élection.": "There must be at least two candidates to start the election.",
    "Êtes-vous sûr de vouloir démarrer l'élection ?\n\nLes étudiants pourront commencer à voter.": "Are you sure you want to start the election?\n\nStudents will be able to start voting.",
    "Êtes-vous sûr de vouloir terminer l'élection ?\n\nAucun vote ne pourra plus être effectué.": "Are you sure you want to end the election?\n\nNo more votes can be cast.",
    "Êtes-vous sûr de vouloir démarrer l'élection ?": "Are you sure you want to start the election?",
    "Êtes-vous sûr de vouloir terminer l'élection ?": "Are you sure you want to end the election?",
    "🚨 ACTION IRRÉVERSIBLE 🚨\n\nÊtes-vous ABSOLUMENT sûr de vouloir réinitialiser l'élection ?\n\nCette action va :\n• Remettre tous les compteurs de votes à zéro\n• Réinitialiser le statut \"a voté\" pour tous les utilisateurs\n• Remettre l'élection en statut \"En attente\"\n\nCette action ne peut pas être annulée !":
        "🚨 IRREVERSIBLE ACTION 🚨\n\nAre you ABSOLUTELY sure you want to reset the election?\n\nThis action will:\n• Reset all vote counters to zero\n• Reset the \"has voted\" status for all users\n• Set the election back to \"Pending\"\n\nThis action cannot be undone!",
    "Pour confirmer la réinitialisation, tapez \"RESET\" ci-dessous :": "To confirm the reset, type \"RESET\" below:",
    "Réinitialisation annulée. Le texte de confirmation ne correspond pas.": "Reset cancelled. The confirmation text does not match.",
    "✅ Élection réinitialisée avec succès !": "✅ Election reset successfully!",
}

I18N_SCRIPT = r"""<script>
/* === Bilingue FR/EN : dictionnaire, t(), traduction du HTML statique, sélecteur === */
(function () {
  var EN = __DICT__;
  var stored = null;
  try { stored = localStorage.getItem('lang'); } catch (e) {}
  var lang = (stored === 'en' || stored === 'fr') ? stored : 'fr';
  window.LANG = lang;
  document.documentElement.lang = lang;

  function saveLang(l) {
    try { localStorage.setItem('lang', l); } catch (e) {}
    var secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = 'lang=' + l + '; path=/; max-age=31536000; SameSite=Lax' + secure;   // lu par le serveur
  }
  saveLang(lang);

  function fill(s, vars) {
    if (!vars) return s;
    return s.replace(/\{(\w+)\}/g, function (m, k) { return (k in vars) ? vars[k] : m; });
  }
  window.t = function (fr, vars) {
    var s = (lang === 'en' && Object.prototype.hasOwnProperty.call(EN, fr)) ? EN[fr] : fr;
    return fill(s, vars);
  };

  function norm(s) { return s.replace(/\s+/g, ' ').trim(); }
  function translateDOM() {
    if (lang !== 'en') return;
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    var nodes = [], n;
    while ((n = walker.nextNode())) {
      var p = n.parentNode && n.parentNode.nodeName;
      if (p !== 'SCRIPT' && p !== 'STYLE') nodes.push(n);
    }
    nodes.forEach(function (node) {
      var key = norm(node.nodeValue);
      if (key && Object.prototype.hasOwnProperty.call(EN, key)) {
        node.nodeValue = node.nodeValue.replace(/\S[\s\S]*\S|\S/, function () { return EN[key]; });
      }
    });
    document.querySelectorAll('[placeholder],[title],[alt],[aria-label]').forEach(function (el) {
      ['placeholder', 'title', 'alt', 'aria-label'].forEach(function (a) {
        var v = el.getAttribute(a);
        if (v && Object.prototype.hasOwnProperty.call(EN, norm(v))) el.setAttribute(a, EN[norm(v)]);
      });
    });
    var title = norm(document.title);
    if (Object.prototype.hasOwnProperty.call(EN, title)) document.title = EN[title];
  }

  document.addEventListener('DOMContentLoaded', function () {
    translateDOM();
    document.querySelectorAll('.lang-switch button').forEach(function (b) {
      if (b.dataset.lang === lang) b.classList.add('active');
      b.addEventListener('click', function () {
        if (b.dataset.lang === lang) return;
        saveLang(b.dataset.lang);
        location.reload();          // tout le contenu dynamique est regénéré dans la nouvelle langue
      });
    });
  });
})();
</script>
"""

LANG_SWITCH_HTML = """        <div class="lang-switch" aria-label="Langue / Language">
            <button type="button" data-lang="fr">FR</button>
            <button type="button" data-lang="en">EN</button>
        </div>
"""

LANG_SWITCH_CSS = """
        /* --- Sélecteur de langue --- */
        .lang-switch { display: flex; justify-content: flex-end; gap: 4px; margin: 10px 0 0; }
        .lang-switch button {
            border: 1px solid #ccc; background: #fff; color: #333; padding: 4px 12px;
            border-radius: 14px; font-size: 0.85rem; font-weight: 600; cursor: pointer;
        }
        .lang-switch button.active { background: var(--primary-color, #1f2a48); color: #fff; border-color: var(--primary-color, #1f2a48); }
"""

report = []


def sub_js(js, pattern, repl, label, flags=re.S, required=False):
    new, n = re.subn(pattern, repl, js, flags=flags)
    report.append((label, n))
    if required and n == 0:
        report[-1] = (label + "  <-- NON TROUVÉ", 0)
    return new


def rep_js(js, old, new, label):
    n = js.count(old)
    report.append((label, n))
    return js.replace(old, new)


def transform_js(js):
    # -- phrases avec variables --------------------------------------------------------------
    js = rep_js(js, "`Merci étudiant(e) ${state.currentUser.prenom} ${state.currentUser.nom} d'avoir voté !`",
                "t(\"Merci étudiant(e) {name} d'avoir voté !\", {name: `${state.currentUser.prenom} ${state.currentUser.nom}`})",
                "message de remerciement")
    js = rep_js(js, "`Bienvenue, ${state.currentUser.prenom} ${state.currentUser.nom}`",
                "t('Bienvenue, {name}', {name: `${state.currentUser.prenom} ${state.currentUser.nom}`})",
                "message de bienvenue")
    js = rep_js(js, "`Erreur ${response.status}`", "t('Erreur {status}', {status: response.status})", "erreur HTTP")
    for old, key in [("`Erreur : ${error.message}`", "Erreur : {msg}"),
                     ("`Erreur lors du vote : ${error.message}`", "Erreur lors du vote : {msg}"),
                     ("`❌ Erreur lors de la réinitialisation : ${error.message}`", "❌ Erreur lors de la réinitialisation : {msg}")]:
        js = rep_js(js, old, "t('%s', {msg: error.message})" % key, "alerte " + key)
    js = sub_js(js, r"`(\$\{users\.length\}) étudiant\(s\) affiché\(s\) sur (\$\{state\.allUsers\.length\})`",
                "t('{n} étudiant(s) affiché(s) sur {m}', {n: users.length, m: state.allUsers.length})",
                "compteur de la recherche")
    js = sub_js(js, r"(Total des (?:inscrits|votes)|Total en attente) : \$\{([^}]*)\}",
                lambda m: "${t('%s : {n}', {n: %s})}" % (m.group(1), m.group(2)), "totaux de la liste")
    js = sub_js(js, r"confirm\(`Êtes-vous sûr de vouloir voter pour \$\{selectedCandidateName\.textContent\} \?(.*?)`\)",
                lambda m: "confirm(t(`Êtes-vous sûr de vouloir voter pour {name} ?%s`, {name: selectedCandidateName.textContent}))" % m.group(1),
                "confirmation du vote")
    js = rep_js(js, "`Êtes-vous sûr de vouloir ${newStatus === 'active' ? 'démarrer' : 'terminer'} l'élection ?`",
                "(newStatus === 'active' ? t(\"Êtes-vous sûr de vouloir démarrer l'élection ?\") : t(\"Êtes-vous sûr de vouloir terminer l'élection ?\"))",
                "confirmation démarrer/terminer")

    # -- alert / confirm / prompt avec un texte simple ---------------------------------------
    def wrap_dialog(m):
        lit = m.group(3)
        if "${" in lit:
            return m.group(0)
        return "%s(t(%s%s%s))" % (m.group(1), m.group(2), lit, m.group(2))
    js = sub_js(js, r"\b(alert|confirm|prompt)\((['\"`])((?:\\.|(?!\2)[^\\])*)\2\)", wrap_dialog, "alert/confirm/prompt")

    # -- chaînes JS simples -------------------------------------------------------------------
    for lit in ["'Les résultats seront annoncés à la fin de la période de vote.'",
                "'Vous pouvez à présent consulter les resultat des votes'",
                "'✅ Données mises à jour'",
                "'Erreur de communication avec le serveur.'",
                "'Erreur de chargement'",
                "'Les mots de passe ne correspondent pas.'",
                '"🟡 En attente"', '"🔴 Terminée"',
                "'En attente'", "'Validée'",
                "' - ❌ Ne peut pas voter'", "' - ✅ A voté'", r"' - ❌ N\'a pas voté'"]:
        js = rep_js(js, lit, "t(%s)" % lit, "chaîne " + lit[:30])

    # -- HTML écrit dans des chaînes '...' (concaténation) -------------------------------------
    def unesc(s):
        return s.replace("\\'", "'")

    def opt_line(line):
        stripped = line.lstrip()
        def r(m):
            key = unesc(m.group(2))
            if stripped.startswith("<option"):                 # dans un gabarit `...`
                return '%s${t("%s")}%s' % (m.group(1), key, m.group(3))
            return "%s' + t(\"%s\") + '%s" % (m.group(1), key, m.group(3))
        return re.sub(r'(<option value="" disabled selected>)((?:Sélectionnez|Erreur)[^<]*)(</option>)', r, line)

    def msg_line(line):
        def r(m):
            return "%s' + t(\"%s\") + '%s" % (m.group(1), unesc(m.group(2)), m.group(3))
        line = re.sub(r"(<div class=\"message message-\w+\">)([^<$]+)(</div>)", r, line)
        line = re.sub(r"(<p>)([^<$]+)(</p>)", r, line) if "innerHTML" in line or "insertAdjacentHTML" in line else line
        return line

    lines = js.split("\n")
    out = []
    for line in lines:
        if line.lstrip().startswith("//") or "console." in line:
            out.append(line)
            continue
        if "<option" in line:
            line = opt_line(line)
        if "message message-" in line or "<p>" in line:
            line = msg_line(line)
        out.append(line)
    js = "\n".join(out)
    report.append(("options <option>, messages <div>, paragraphes <p>", "ok"))

    # -- HTML écrit dans des gabarits `...` ---------------------------------------------------------
    js = sub_js(js, r"(?m)^(\s*<i class=\"[^\"]*\"></i>)[ \t]+([A-Za-zÀ-ÿ][^<$`\n]*?)[ \t]*$",
                lambda m: '%s ${t("%s")}' % (m.group(1), m.group(2).replace('"', '\\"')), "icône + texte (boutons)",
                flags=0)
    js = sub_js(js, r"(<i class=\"fas fa-robot\"></i>) (Contrôle automatique du reçu)(</strong>)",
                r'\1 ${t("\2")}\3', "contrôle automatique")
    js = sub_js(js, r"(<button class=\"btn btn-danger\" data-candidate-id=\"\$\{candidate\.id\}\">)Supprimer(</button>)",
                r'\1${t("Supprimer")}\2', "bouton supprimer candidat", flags=0)
    js = sub_js(js, r"<strong>(Spécialité:|Niveau:|Bureau:)</strong>", r'<strong>${t("\1")}</strong>', "libellés carte candidat")
    js = sub_js(js, r"(<div class=\"stat-label\">)([^<]+)(</div>)", r'\1${t("\2")}\3', "libellés statistiques")
    js = sub_js(js, r"<strong>Attention :</strong> (La réinitialisation effacera tous les votes et remettra l'élection à zéro\.)",
                r'<strong>${t("Attention :")}</strong> ${t("\1")}', "avertissement réinitialisation")
    js = sub_js(js, r"(?m)^(\s*)Appuyez sur Échap ou cliquez sur (<i class=\"fas fa-times\"></i>) pour fermer",
                r'\1${t("Appuyez sur Échap ou cliquez sur")} \2 ${t("pour fermer")}', "aide du tutoriel")
    js = sub_js(js, r'title="Tutoriel de la plateforme de vote"', 'title="${t(\'Tutoriel de la plateforme de vote\')}"', "titre iframe")
    return js


def main(path):
    html = open(path, encoding="utf-8").read()
    if "window.t = function" in html:
        sys.exit("Déjà appliqué : rien à faire.")
    shutil.copyfile(path, path + ".bak")

    # 1) CSS du sélecteur
    html = html.replace("</style>", LANG_SWITCH_CSS + "    </style>", 1)

    # 2) sélecteur de langue en haut de <main>
    html, n = re.subn(r'(<main class="container">\s*\n)', lambda m: m.group(1) + LANG_SWITCH_HTML, html, count=1)
    report.append(("sélecteur de langue ajouté dans <main>", n))

    # 3) bloc i18n avant le script principal, et traduction du JS principal
    i = html.index("<script>", html.index("<body"))
    j = html.index("</script>", i)
    js = transform_js(html[i:j])
    block = I18N_SCRIPT.replace("__DICT__", json.dumps(EN, ensure_ascii=False, indent=2))
    html = html[:i] + block + "\n" + js + html[j:]

    open(path, "w", encoding="utf-8").write(html)

    print("Rapport (nombre de remplacements) :")
    for label, n in report:
        print(f"  {n!s:>3}  {label}")
    print("\nSauvegarde : " + path + ".bak")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
