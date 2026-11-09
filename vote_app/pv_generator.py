from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.platypus import Image

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

BLEU = colors.HexColor('#24284B')
ORANGE = colors.HexColor('#E87722')
GRIS = colors.HexColor('#f4f4f4')
GAGNANT = colors.HexColor('#fdebd8')


def _pct(part, total):
    v = (part / total * 100) if total else 0
    return f"{v:.2f}".replace('.', ',') + ' %'


def build_pv_pdf(d):
    """d : dictionnaire préparé par la vue (voir pv_pdf_view). Retourne les octets du PDF."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title=f"PV élection Gouverneur AESP {d['annee']}", author='AESP')

    ss = getSampleStyleSheet()
    normal = ParagraphStyle('n', parent=ss['Normal'], fontName='Helvetica',
                            fontSize=10.5, leading=15, alignment=TA_JUSTIFY)
    cell = ParagraphStyle('c', parent=normal, fontSize=9.5, leading=12, alignment=0)
    cell_c = ParagraphStyle('cc', parent=cell, alignment=TA_CENTER)
    cell_h = ParagraphStyle('ch', parent=cell_c, fontName='Helvetica-Bold', textColor=colors.white)
    titre = ParagraphStyle('t', parent=ss['Title'], fontName='Helvetica-Bold',
                           fontSize=17, leading=21, textColor=BLEU, spaceAfter=2)
    sous = ParagraphStyle('s', parent=normal, alignment=TA_CENTER, textColor=colors.HexColor('#555555'))
    h2 = ParagraphStyle('h2', parent=normal, fontName='Helvetica-Bold', fontSize=12,
                        textColor=BLEU, spaceBefore=14, spaceAfter=6, alignment=0)

    def P(txt, st=cell):
        return Paragraph(escape(str(txt)), st)

    def tableau(rows, widths, header=True, extra=None):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbbbbb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if header:
            style += [('BACKGROUND', (0, 0), (-1, 0), BLEU)]
            style += [('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS])]
        style += extra or []
        t.setStyle(TableStyle(style))
        return t

    total, inscrits, votants = d['total_votes'], d['inscrits'], d['votants']
    s = []

    # ---------- En-tête avec logos ----------
    def _logo(path, max_h=1.8 * cm, max_w=3.2 * cm):
        if not path:
            return Paragraph('', normal)
        try:
            img = Image(path)
            ratio = img.imageWidth / img.imageHeight
            h = max_h
            w = h * ratio
            if w > max_w:
                w = max_w
                h = w / ratio
            img.drawWidth, img.drawHeight = w, h
            return img
        except Exception:
            return Paragraph('', normal)

    bloc_titre = [P("ASSOCIATION DES ÉTUDIANTS DE SOUTH POLYTECH (AESP)", sous),
                  Spacer(1, 4),
                  P("PROCÈS-VERBAL DES RÉSULTATS", titre),
                  P(f"Élection du Gouverneur de l'AESP — Année académique {d['annee']}", sous)]

    entete = Table(
        [[_logo(d.get('logo_iuget')), bloc_titre, _logo(d.get('logo_aesp'))]],
        colWidths=[3.4 * cm, 10.2 * cm, 3.4 * cm])
    entete.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    s += [entete, Spacer(1, 6)]

    barre = Table([['']], colWidths=[17 * cm], rowHeights=[3])
    barre.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), ORANGE)]))
    s += [barre, Spacer(1, 10)]
    
    # ---------- Préambule ----------
    s.append(P(
        f"Le présent procès-verbal est établi à l'issue du scrutin pour l'élection du Gouverneur "
        f"de l'AESP, organisé en ligne {escape(d['periode'])}. Il consigne les résultats du "
        f"dépouillement électronique, arrêtés à la clôture du scrutin, et a été édité le "
        f"{d['edite_le']} par {escape(d['edite_par'])}.", normal))

    # ---------- 1. Participation ----------
    s.append(P("1. Récapitulatif de la participation", h2))
    rows = [
        [P('Électeurs inscrits (comptes validés)'), P(inscrits, cell_c)],
        [P('Votants'), P(votants, cell_c)],
        [P('Abstentions'), P(inscrits - votants, cell_c)],
        [P('Taux de participation'), P(_pct(votants, inscrits), cell_c)],
        [P('Taux d\'abstention'), P(_pct(inscrits - votants, inscrits), cell_c)],
        [P('Bulletins blancs ou nuls'), P(0, cell_c)],
        [P('Suffrages exprimés'), P(total, cell_c)],
    ]
    s.append(tableau(rows, [11 * cm, 6 * cm], header=False,
                     extra=[('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, GRIS]),
                            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold')]))
    s.append(Spacer(1, 4))
    s.append(P("Le système de vote en ligne n'enregistre pas de bulletins blancs ou nuls : "
               "tout vote enregistré est un suffrage exprimé en faveur d'un candidat.",
               ParagraphStyle('note', parent=cell, fontSize=8.5, textColor=colors.HexColor('#666666'))))

    # ---------- 2. Classement ----------
    s.append(P("2. Résultats et classement des candidats", h2))
    rows = [[P(h, cell_h) for h in ('Rang', 'Candidat', 'Bureau', 'Voix', '% exprimés', '% inscrits')]]
    extra = []
    for i, c in enumerate(d['classement'], start=1):
        rows.append([P(c['rang'], cell_c), P(c['nom']), P(c['bureau']), P(c['voix'], cell_c),
                     P(_pct(c['voix'], total), cell_c), P(_pct(c['voix'], inscrits), cell_c)])
        if c['rang'] == 1 and total:
            extra.append(('BACKGROUND', (0, i), (-1, i), GAGNANT))
    s.append(tableau(rows, [1.3 * cm, 5.2 * cm, 4 * cm, 1.8 * cm, 2.4 * cm, 2.3 * cm], extra=extra))

    # ---------- 3. Proclamation ----------
    s.append(P("3. Proclamation", h2))
    tete = [c for c in d['classement'] if c['rang'] == 1]
    if total == 0:
        txt = "Aucun suffrage n'a été enregistré : aucun candidat ne peut être proclamé élu."
    elif len(tete) > 1:
        noms = ', '.join(escape(c['nom']) for c in tete)
        txt = (f"<b>Égalité parfaite</b> entre {noms} avec {tete[0]['voix']} voix chacun "
               f"({_pct(tete[0]['voix'], total)} des suffrages exprimés). Aucun candidat ne peut être "
               f"proclamé élu : il appartient à la commission électorale de décider du départage.")
    else:
        g = tete[0]
        maj = 'à la majorité absolue' if g['voix'] * 2 > total else 'à la majorité relative'
        txt = (f"Au vu des résultats ci-dessus, <b>{escape(g['nom'])}</b> (bureau « {escape(g['bureau'])} ») "
               f"est proclamé(e) élu(e) Gouverneur(e) de l'AESP pour l'année académique {d['annee']}, "
               f"{maj}, avec <b>{g['voix']} voix</b> sur {total} suffrages exprimés, soit "
               f"<b>{_pct(g['voix'], total)}</b>.")
    s.append(P(txt, normal))

    # ---------- 4. Observations ----------
    s.append(P("4. Observations", h2))
    s.append(P("Dépouillement réalisé automatiquement par la plateforme de vote en ligne. Chaque électeur "
               "n'a pu voter qu'une seule fois (un compte, un vote). Les inscriptions ont été validées "
               "soit automatiquement après contrôle du reçu, soit manuellement par un administrateur. "
               "Toute réclamation doit être adressée à la commission électorale.", normal))
    s.append(Spacer(1, 4))
    s.append(P("Observations complémentaires : " + "." * 120, normal))
    s.append(P("." * 140, normal))

    # ---------- Signatures ----------
    sig = Table(
        [[P('Le Président de la Commission électorale', cell_c),
          P('Responsable de la vie Estudiantine', cell_c),
          P("Directeur de South Polytech", cell_c)],
         ['', '', '']],
        colWidths=[5.6 * cm] * 3, rowHeights=[None, 2.4 * cm])
    sig.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                             ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                             ('BACKGROUND', (0, 0), (-1, 0), GRIS)]))
    cand = [[P('Candidat (ou son représentant)', cell_h), P('Signature', cell_h)]]
    for c in d['classement']:
        cand.append([P(c['nom']+" "+c['prenom']), ''])
    ct = tableau(cand, [9 * cm, 8 * cm])
    ct.setStyle(TableStyle([('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
                            ('TOPPADDING', (0, 1), (-1, -1), 14), ('BOTTOMPADDING', (0, 1), (-1, -1), 14)]))
    s.append(KeepTogether([P("Fait à Douala, le ________________", ParagraphStyle('r', parent=normal, alignment=2)),
                           Spacer(1, 8), P("Signatures de la commission électorale", h2), sig,
                           Spacer(1, 6), P("Prise de connaissance des candidats", h2), ct]))

    def pied(canvas, doc_):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(2 * cm, 1.1 * cm, f"PV élection Gouverneur AESP {d['annee']} — contrôle : {d['empreinte']}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(s, onFirstPage=pied, onLaterPages=pied)
    return buf.getvalue()