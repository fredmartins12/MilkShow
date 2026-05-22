# -*- coding: utf-8 -*-
"""
Gera MilkShow_Centelha_Fase1.pdf a partir de centelha_fase1.md
Uso: py -3 docs/gerar_centelha_pdf.py
"""
import re, os
from pathlib import Path
from fpdf import FPDF

DOCS    = Path(__file__).parent
MD_FILE = DOCS / "centelha_fase1.md"
OUT     = DOCS / "MilkShow_Centelha_Fase1.pdf"

# Normaliza caracteres especiais para latin-1
def norm(txt):
    return (txt
        .replace('\u2014', '-')   # em dash
        .replace('\u2013', '-')   # en dash
        .replace('\u2019', "'")   # curly apostrophe
        .replace('\u2018', "'")
        .replace('\u201c', '"')
        .replace('\u201d', '"')
        .replace('\u00e9', 'e')   # letras acentuadas comuns ficam via latin-1
        .replace('\u2192', '->')
        .replace('\u2265', '>=')
        .replace('\u2264', '<=')
        .replace('\u00b0', 'o')
        .encode('latin-1', errors='replace').decode('latin-1')
    )

def strip_md(txt):
    txt = re.sub(r'\*\*(.+?)\*\*', r'\1', txt)
    txt = re.sub(r'\*(.+?)\*',     r'\1', txt)
    txt = re.sub(r'`(.+?)`',       r'\1', txt)
    return txt.strip()

GREEN  = (22, 163, 74)
DGREEN = (14, 100, 48)
BLACK  = (30, 30, 30)
GRAY   = (90, 90, 90)
LGRAY  = (150, 150, 150)
WHITE  = (255, 255, 255)

class PitchPDF(FPDF):
    def header(self):
        self.set_fill_color(*GREEN)
        self.rect(0, 0, 210, 6, 'F')

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(*LGRAY)
        self.cell(0, 4, norm('MilkShow - Centelha PB - FAPESQ-PB / MCTIC'), align='L')
        self.cell(0, 4, f'Pagina {self.page_no()}', align='R')

pdf = PitchPDF()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(18, 14, 18)
pdf.add_page()

lines = MD_FILE.read_text(encoding='utf-8').split('\n')
in_table = False

for raw in lines:
    line = raw.rstrip()

    # ── H1
    if re.match(r'^# [^#]', line):
        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 17)
        pdf.set_text_color(*GREEN)
        pdf.multi_cell(0, 9, norm(line[2:]))
        pdf.ln(1)

    # ── H2
    elif re.match(r'^## [^#]', line):
        pdf.ln(5)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(0, 7, norm(line[3:]))
        pdf.set_draw_color(*GREEN)
        pdf.set_line_width(0.4)
        pdf.line(18, pdf.get_y()+1, 192, pdf.get_y()+1)
        pdf.ln(4)
        in_table = False

    # ── H3
    elif re.match(r'^### [^#]', line):
        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*DGREEN)
        pdf.multi_cell(0, 6, norm(line[4:]))
        pdf.ln(1)
        in_table = False

    # ── table separator (skip)
    elif re.match(r'^\|[\s\-|]+\|$', line):
        pass

    # ── table row
    elif line.startswith('|'):
        cells = [strip_md(c.strip()) for c in line.strip('|').split('|')]
        n = len(cells)
        w = 174 / n
        is_header = not in_table
        in_table = True
        if is_header:
            pdf.set_fill_color(235, 250, 240)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(*DGREEN)
        else:
            pdf.set_fill_color(*WHITE)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(*GRAY)
        pdf.set_draw_color(200, 220, 205)
        for c in cells:
            pdf.cell(w, 6, norm(c[:55]), border=1, fill=True)
        pdf.ln()

    # ── HR ---
    elif re.match(r'^-{3,}$', line):
        pdf.ln(3)
        pdf.set_draw_color(210, 210, 210)
        pdf.set_line_width(0.2)
        pdf.line(18, pdf.get_y(), 192, pdf.get_y())
        pdf.ln(4)
        in_table = False

    # ── bullet
    elif line.startswith('- '):
        in_table = False
        txt = norm(strip_md(line[2:]))
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*GRAY)
        # bullet symbol
        x, y = pdf.get_x(), pdf.get_y()
        pdf.set_fill_color(*GREEN)
        pdf.ellipse(x+1, y+1.8, 2, 2, 'F')
        pdf.set_x(x+5)
        pdf.multi_cell(0, 5, txt)
        pdf.ln(0.5)

    # ── bold standalone label (e.g. **Nome:**)
    elif re.match(r'^\*\*.+\*\*', line) and len(line) < 90:
        in_table = False
        label_m = re.match(r'^\*\*(.+?)\*\*(.*)$', line)
        if label_m:
            label = norm(label_m.group(1))
            rest  = norm(strip_md(label_m.group(2)))
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(*DGREEN)
            pdf.write(5, label)
            if rest.strip():
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(*GRAY)
                pdf.write(5, rest)
            pdf.ln(5)
        else:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(0, 5, norm(strip_md(line)))

    # ── italic footnote
    elif re.match(r'^\*.+\*$', line) and not line.startswith('**'):
        in_table = False
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(*LGRAY)
        pdf.multi_cell(0, 4, norm(line.strip('*')))
        pdf.ln(1)

    # ── blank line
    elif line.strip() == '':
        in_table = False
        pdf.ln(2)

    # ── normal paragraph
    else:
        in_table = False
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*GRAY)
        pdf.multi_cell(0, 5, norm(strip_md(line)))
        pdf.ln(1)

pdf.output(str(OUT))
kb = OUT.stat().st_size // 1024
print(f"PDF gerado: {OUT}  ({kb} KB)")
os.startfile(str(OUT))
