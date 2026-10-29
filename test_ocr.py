import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "election_project.settings")
django.setup()

from vote_app import receipt_verifier as rv

with open(sys.argv[1], "rb") as f:
    jpeg, _ = rv.prepare_image(f)          # même image que celle utilisée par l'application

print("TEXTE BRUT :\n", rv.ocrspace_request(jpeg))
d = rv.extract_receipt_fields(jpeg)         # texte OCR + QR code
if not d.get('nom_complet'):
    print("PAS DE NOM NOUVELLE TENTATIVE !!!")
    d = rv.extract_receipt_fields(jpeg)         # texte OCR + QR code
print("\nCHAMPS EXTRAITS :\n", d)
if d:
    print("\nQR CODE :", d.get("qr_raw"))
    print("Matricule QR :", d.get("qr_matricule"), "| matricule imprimé :", d.get("matricule"))
    print("Année QR :", d.get("qr_annee_academique"), "| année imprimée :", d.get("annee_academique"))
    form = {"nom": "", "prenom": "", "matricule": input("\nMatricule saisi (Entrée = celui du reçu) : ") or d.get("matricule")}
    form["nom"] = d.get("nom_complet") or ""
    v = rv.compare(form, d)
    print("\n" + v.note())
