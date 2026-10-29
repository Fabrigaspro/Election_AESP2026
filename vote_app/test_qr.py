"""Tests du contrôle par QR code : python manage.py test vote_app.test_qr"""
import io
from unittest import mock

import cv2
import numpy as np
from django.test import SimpleTestCase, override_settings

from . import receipt_verifier as rv

FORM = dict(nom="FONGANG", prenom="LAMAGO BRANK", matricule="24IU85885",
            cycle="ingenieur", niveau="1", campus="Bonamoussadi",
            specialite="GI", specialite_label="Genie Informatique")
CFG = dict(academic_year="2026/2027", expected_amount=0)
QR = "24IU85885|2026/2027|f0c5c1ad1a8f92e75300480d87f7de5af0f5575a79e6c3117f824daa5a4f9306"


def extract(**kw):
    d = dict(is_receipt=True, is_legible=True, matricule="24IU85885", nom_complet="FONGANG LAMAGO BRANK",
             campus="BONAMOUSSADI", cycle="INGENIEUR", niveau="1", annee_academique="2026/2027",
             confidence=0.9, anomalies=[])
    d.update(rv.parse_qr_payload(QR))
    d.update(kw)
    return d


def names(v, ok=False):
    return [c.name for c in v.checks if c.ok == ok]


class QrParseTests(SimpleTestCase):
    def test_payload(self):
        p = rv.parse_qr_payload(QR)
        self.assertEqual(p["qr_matricule"], "24IU85885")
        self.assertEqual(p["qr_annee_academique"], "2026/2027")
        self.assertTrue(p["qr_signature"].startswith("f0c5"))

    def test_payload_incomplet(self):
        p = rv.parse_qr_payload("https://exemple.com")
        self.assertIsNone(p["qr_annee_academique"])

    def test_decode_qr_image_generee(self):
        enc = cv2.QRCodeEncoder.create()
        qr = enc.encode(QR)
        qr = cv2.resize(qr, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
        page = np.full((1000, 800), 255, np.uint8)
        page[700:700 + qr.shape[0], 40:40 + qr.shape[1]] = qr[:300, :300] if qr.shape[0] > 300 else qr
        ok, buf = cv2.imencode(".jpg", page)
        self.assertEqual(rv.decode_qr(buf.tobytes()), QR)

    def test_decode_qr_absent(self):
        ok, buf = cv2.imencode(".jpg", np.full((400, 400), 255, np.uint8))
        self.assertIsNone(rv.decode_qr(buf.tobytes()))


class QrCompareTests(SimpleTestCase):
    def test_tout_conforme(self):
        v = rv.compare(FORM, extract(), CFG)
        self.assertTrue(v.validated, v.failed_reasons())
        for n in ("qr_matricule", "qr_matricule_texte", "qr_annee", "qr_annee_texte"):
            self.assertIn(n, names(v, True))

    def test_qr_matricule_different_du_formulaire(self):
        v = rv.compare(FORM, extract(qr_matricule="24IU00000"), CFG)
        self.assertFalse(v.validated)
        self.assertIn("qr_matricule", names(v))

    def test_qr_matricule_different_du_texte(self):
        # formulaire = texte imprimé, mais QR d'un autre étudiant : fraude par montage
        v = rv.compare(FORM, extract(qr_matricule="24IU11111"), CFG)
        self.assertFalse(v.validated)
        self.assertIn("qr_matricule_texte", names(v))

    def test_qr_mauvaise_annee(self):
        v = rv.compare(FORM, extract(qr_annee_academique="2025/2026"), CFG)
        self.assertFalse(v.validated)
        self.assertIn("qr_annee", names(v))

    def test_qr_annee_differente_du_texte(self):
        v = rv.compare(FORM, extract(annee_academique="2025/2026"), CFG)
        self.assertFalse(v.validated)

    def test_confusion_O_0_toleree(self):
        v = rv.compare(FORM, extract(qr_matricule="24IU858B5".replace("B", "8")), CFG)
        self.assertTrue(v.validated)

    def test_qr_illisible_charge_inutile(self):
        v = rv.compare(FORM, extract(qr_raw="n'importe quoi", qr_matricule=None, qr_annee_academique=None), CFG)
        self.assertFalse(v.validated)

    def test_sans_qr_valide_par_defaut(self):
        v = rv.compare(FORM, extract(qr_raw=None, qr_matricule=None, qr_annee_academique=None), CFG)
        self.assertTrue(v.validated)

    @override_settings(RECEIPT_REQUIRE_QR=True)
    def test_sans_qr_refuse_si_obligatoire(self):
        v = rv.compare(FORM, extract(qr_raw=None, qr_matricule=None, qr_annee_academique=None), CFG)
        self.assertFalse(v.validated)
        self.assertIn("qr", names(v))


class QrExtractTests(SimpleTestCase):
    def test_extract_ajoute_les_champs_qr(self):
        with mock.patch.object(rv, "extract_text_fields", return_value={"matricule": "x"}), \
             mock.patch.object(rv, "decode_qr", return_value=QR):
            d = rv.extract_receipt_fields(b"j")
        self.assertEqual(d["qr_matricule"], "24IU85885")
        self.assertEqual(d["qr_annee_academique"], "2026/2027")

    def test_extract_sans_qr(self):
        with mock.patch.object(rv, "extract_text_fields", return_value={"matricule": "x"}), \
             mock.patch.object(rv, "decode_qr", return_value=None):
            d = rv.extract_receipt_fields(b"j")
        self.assertIsNone(d["qr_raw"])

    def test_texte_illisible_reste_none(self):
        with mock.patch.object(rv, "extract_text_fields", return_value=None):
            self.assertIsNone(rv.extract_receipt_fields(b"j"))


class OcrSpaceRetryTests(SimpleTestCase):
    SANS_NOM = "RECU PENSION\nIUGET\nMatricule : 24IU85885\nCampus : BONAMOUSSADI A\n"
    AVEC_NOM = SANS_NOM + "Nom et Prénom : FONGANG LAMAGO BRANK CHARESTE\nNiveau : 3\n"

    @override_settings(OCR_SPACE_API_KEY="k")
    def test_reessaie_quand_le_nom_manque(self):
        with mock.patch.object(rv, "ocrspace_request", side_effect=[self.SANS_NOM, self.AVEC_NOM]) as m:
            d = rv.extract_with_ocrspace(b"x")
        self.assertEqual(m.call_count, 2)
        self.assertEqual(d["nom_complet"], "FONGANG LAMAGO BRANK CHARESTE")
        self.assertTrue(d["is_legible"])
        self.assertEqual(m.call_args_list[0].kwargs["engine"], 2)
        self.assertEqual(m.call_args_list[1].kwargs["engine"], 1)

    @override_settings(OCR_SPACE_API_KEY="k")
    def test_un_seul_appel_si_tout_est_lu(self):
        with mock.patch.object(rv, "ocrspace_request", return_value=self.AVEC_NOM) as m:
            d = rv.extract_with_ocrspace(b"x")
        self.assertEqual(m.call_count, 1)
        self.assertTrue(d["is_legible"])

    @override_settings(OCR_SPACE_API_KEY="k", OCR_SPACE_MAX_RETRIES=2)
    def test_nom_jamais_lu_apres_les_essais(self):
        with mock.patch.object(rv, "ocrspace_request", return_value=self.SANS_NOM) as m:
            d = rv.extract_with_ocrspace(b"x")
        self.assertEqual(m.call_count, 3)
        self.assertFalse(d["is_legible"])      # -> inscription en attente de vérification manuelle

    @override_settings(OCR_SPACE_API_KEY="k")
    def test_erreur_puis_succes(self):
        with mock.patch.object(rv, "ocrspace_request", side_effect=[TimeoutError("x"), self.AVEC_NOM]):
            d = rv.extract_with_ocrspace(b"x")
        self.assertEqual(d["matricule"], "24IU85885")

    @override_settings(OCR_SPACE_API_KEY="k")
    def test_toutes_les_erreurs_donnent_none(self):
        with mock.patch.object(rv, "ocrspace_request", side_effect=TimeoutError("x")):
            self.assertIsNone(rv.extract_with_ocrspace(b"x"))


class EcoleTests(SimpleTestCase):
    def test_ecole_conforme(self):
        v = rv.compare(FORM, extract(ecole="SOUTH POLYTECH"), dict(CFG, ecole="SOUTH POLYTECH"))
        self.assertTrue(v.validated, v.failed_reasons())
        self.assertIn("ecole", names(v, True))

    def test_ecole_espaces_perdus(self):
        v = rv.compare(FORM, extract(ecole="SouthPolytech"), dict(CFG, ecole="SOUTH POLYTECH"))
        self.assertTrue(v.validated, v.failed_reasons())

    def test_autre_ecole_refusee(self):
        v = rv.compare(FORM, extract(ecole="ENSET"), dict(CFG, ecole="SOUTH POLYTECH"))
        self.assertFalse(v.validated)
        self.assertIn("ecole", names(v))

    def test_ecole_non_lue_bloque_par_defaut(self):
        v = rv.compare(FORM, extract(ecole=None), dict(CFG, ecole="SOUTH POLYTECH"))
        self.assertFalse(v.validated)

    def test_ecole_non_lue_toleree_si_non_requise(self):
        v = rv.compare(FORM, extract(ecole=None), dict(CFG, ecole="SOUTH POLYTECH", require_ecole=False))
        self.assertTrue(v.validated, v.failed_reasons())

    def test_aucune_ecole_configuree_pas_de_controle(self):
        v = rv.compare(FORM, extract(ecole="ENSET"), dict(CFG, ecole=""))
        self.assertTrue(v.validated)

    def test_etiquette_ecole_ignore_entete(self):
        rows = rv.ocrspace_text_to_rows("ÉCOLES DES TROPIQUES (IUGET)\nÉcole : SOUTH POLYTECH\nMatricule : 1\n")
        self.assertEqual(rv.parse_ocr_rows(rows)["ecole"], "SOUTH POLYTECH")
