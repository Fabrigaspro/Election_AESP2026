"""Diagnostic QR : python diag_qr.py chemin\\recu2.jpg   (à lancer depuis le dossier de manage.py)"""
import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "election_project.settings")
django.setup()
from vote_app import receipt_verifier as rv

try:
    import zxingcpp
    print("zxing-cpp  : INSTALLÉ", getattr(zxingcpp, "__version__", ""))
except ImportError:
    print("zxing-cpp  : ABSENT  -> faites : pip install zxing-cpp")
print("opencv     :", "installé " + rv.cv2.__version__ if rv.cv2 else "ABSENT")

raw = open(sys.argv[1], "rb").read()
with open(sys.argv[1], "rb") as f:
    prepared, _ = rv.prepare_image(f)
print("image originale :", rv.decode_qr(raw))
print("image préparée (1600 px, celle de l'appli) :", rv.decode_qr(prepared))
