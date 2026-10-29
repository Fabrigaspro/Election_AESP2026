# Vérification automatique du reçu pension IUGET — mise à jour (fusionnée avec TON projet actuel)

## Fichiers à remplacer (mêmes chemins que dans ton projet)
- vote_app/receipt_verifier.py  (lecture du reçu : OCR local + Claude optionnel, règles de comparaison)
- vote_app/views.py             (transmet cycle, niveau, campus, spécialité ; mot de passe retiré des logs)
- vote_app/tests.py             (52 tests)
- vote_app/templates/vote_app/index.html (texte d'aide ; ton libellé « Photo du reçu IUGET » est conservé)
- election_project/settings.py  (bloc IA qui manquait : moteur, année académique, seuils)
Ton models.py (correctif de session) et ta migration 0028 restent inchangés.

## Installation
pip install -r requirements.additions.txt     (Pillow, anthropic, rapidocr-onnxruntime)
python manage.py test vote_app

## Moteurs de lecture (variable RECEIPT_ENGINE, défaut « auto »)
- OCR local (rapidocr-onnxruntime) : AUCUNE clé, aucun coût, rien n'est envoyé à l'extérieur.
  ~2,5 s par reçu, ~480 Mo de mémoire. C'est le moteur utilisé tant que ANTHROPIC_API_KEY n'existe pas.
- Claude (vision) : utilisé en priorité si ANTHROPIC_API_KEY est définie ; l'OCR prend le relais si l'appel échoue.
  Plus tolérant aux photos de téléphone et détecte des retouches visibles.
- Si aucun moteur n'est disponible : l'inscription reste « en attente » (validation manuelle).

## Si l'OCR échoue au déploiement sur Railway avec « libGL.so.1 »
Ajoute les paquets système libgl1 et libglib2.0-0 à l'image (nixpacks.toml : aptPkgs), ou passe RECEIPT_ENGINE=claude.
