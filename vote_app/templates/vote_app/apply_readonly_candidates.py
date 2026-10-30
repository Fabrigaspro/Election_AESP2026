#!/usr/bin/env python3
"""Électeurs : voir les candidats sans pouvoir voter tant que l'élection n'est pas active.

Usage :  python apply_readonly_candidates.py chemin/vers/index.html
Crée index.html.bak puis modifie le fichier. S'arrête sans rien écrire si un passage est introuvable.
"""
import re
import shutil
import sys


def main(path):
    raw = open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    html = raw.replace("\r\n", "\n")

    if "voteInstructionsText" in html:
        sys.exit("Déjà appliqué : rien à faire.")

    def once(old, new, label):
        nonlocal html
        if html.count(old) != 1:
            sys.exit(f"ERREUR : passage introuvable ou en double ({label}). Rien n'a été modifié.")
        html = html.replace(old, new)
        print("  ok  ", label)

    # 1) identifiant sur la phrase d'instructions
    once("<p>Choisissez votre candidat préféré en cliquant sur sa carte. Vous ne pourrez voter qu'une seule fois !</p>",
         '<p id="voteInstructionsText">Choisissez votre candidat préféré en cliquant sur sa carte. '
         "Vous ne pourrez voter qu'une seule fois !</p>",
         "phrase d'instructions")

    # 2) élection en attente : on affiche le message ET les candidats (plus de return)
    once("""            if (state.electionStatus == 'pending') {
                electionStatusMessage.innerHTML = '<div class="message message-warning">' + t("L'élection n'est pas encore ouverte.") + '</div>';
                return;
            }
""",
         """            // Le vote n'est possible que si l'élection est active
            const canVote = state.electionStatus === 'active';
            candidatesForVote.classList.toggle('readonly', !canVote);
            const voteInstructions = document.getElementById('voteInstructionsText');
            if (voteInstructions) {
                voteInstructions.textContent = (state.electionStatus === 'pending')
                    ? t("Découvrez les candidats ci-dessous. Le vote sera possible dès l'ouverture de l'élection.")
                    : t("Choisissez votre candidat préféré en cliquant sur sa carte. Vous ne pourrez voter qu'une seule fois !");
            }
            if (state.electionStatus == 'pending') {
                electionStatusMessage.innerHTML = '<div class="message message-warning">' + t("L'élection n'est pas encore ouverte. Le vote sera possible dès son ouverture.") + '</div>';
                // pas de return : les candidats restent visibles, sans bouton de vote
            }
""",
         "élection en attente : candidats visibles")

    # 3) bouton de vote seulement si l'élection est active
    once("""                    <button class="vote-btn" data-candidate-id="${candidate.id}">
                        <i class="fas fa-vote-yea"></i> ${t("Choisir ce candidat")}
                    </button>
                `;""",
         """                    ${canVote ? `<button class="vote-btn" data-candidate-id="${candidate.id}">
                        <i class="fas fa-vote-yea"></i> ${t("Choisir ce candidat")}
                    </button>` : ''}
                `;""",
         "bouton « Choisir ce candidat » conditionnel")

    # 4) garde-fou dans le gestionnaire de clic
    once("""        candidatesForVote.addEventListener('click', (e) => {
""",
         """        candidatesForVote.addEventListener('click', (e) => {
            if (state.electionStatus !== 'active') return;   // consultation seule
""",
         "garde-fou au clic")

    # 5) CSS : plus d'effet « cliquable » en lecture seule
    once("</style>",
         "        .candidates-grid.readonly .candidate-card:hover { transform: none; box-shadow: 0 8px 25px rgba(0,0,0,0.1); }\n    </style>",
         "CSS lecture seule")

    # 6) traductions anglaises (si le dictionnaire bilingue est présent)
    new_keys = (
        '  "Découvrez les candidats ci-dessous. Le vote sera possible dès l\'ouverture de l\'élection.": '
        '"Discover the candidates below. Voting will be possible as soon as the election opens.",\n'
        '  "L\'élection n\'est pas encore ouverte. Le vote sera possible dès son ouverture.": '
        '"The election is not open yet. Voting will be possible as soon as it opens.",\n'
    )
    html, n = re.subn(r"(var EN = \{\n)", lambda m: m.group(1) + new_keys, html, count=1)
    print("  ok   traductions EN ajoutées" if n else "  --   dictionnaire EN absent (version non bilingue) : ignoré")

    shutil.copyfile(path, path + ".bak")
    open(path, "w", encoding="utf-8", newline="").write(html.replace("\n", nl))
    print("Sauvegarde :", path + ".bak")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
