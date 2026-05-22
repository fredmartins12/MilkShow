"""
Converte documentacao_tecnica.md -> documentacao_tecnica.pdf usando fpdf2 + markdown.
"""
import re
import markdown
from fpdf import FPDF

def _safe(text: str) -> str:
    """Substitui caracteres fora do latin-1 por equivalentes ASCII."""
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2019': "'",    # right single quote
        '\u2018': "'",    # left single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2022': '*',    # bullet
        '\u25ba': '>',    # arrow
        '\u25c4': '<',
        '\u2500': '-',    # box drawing
        '\u2502': '|',
        '\u251c': '+',
        '\u2514': '+',
        '\u2510': '+',
        '\u250c': '+',
        '\u2518': '+',
        '\u252c': '+',
        '\u2524': '+',
        '\u2534': '+',
        '\u253c': '+',
        '\u2550': '=',
        '\u2554': '+',
        '\u2557': '+',
        '\u255a': '+',
        '\u255d': '+',
        '\u2560': '+',
        '\u2563': '+',
        '\u2566': '+',
        '\u2569': '+',
        '\u256c': '+',
        '\u25b6': '>',
        '\u25c4': '<',
        '\u2192': '->',
        '\u2190': '<-',
        '\u2193': 'v',
        '\u2191': '^',
        '\u00e3': 'a',    # a tilde (fallback)
        '\u00e7': 'c',
        '\u00e9': 'e',
        '\u00ea': 'e',
        '\u00e0': 'a',
        '\u00e1': 'a',
        '\u00e2': 'a',
        '\u00e4': 'a',
        '\u00f3': 'o',
        '\u00f4': 'o',
        '\u00fa': 'u',
        '\u00fc': 'u',
        '\u00ed': 'i',
        '\u00f5': 'o',
        '\u00c3': 'A',
        '\u00c9': 'E',
        '\u00c7': 'C',
        '\u00d3': 'O',
        '\u00da': 'U',
        '\u00b0': 'o',    # degree sign
        '\u00b7': '.',
        '\u25ae': '#',
        '\u25aa': '-',
        '\u2588': '#',
        '\u2591': '.',
        '\u2592': '+',
        '\u2593': '#',
        '\u25a0': '#',
        '\u25a1': '[]',
        '\u2b25': '<>',
        '\u2665': 'v',
        '\u2764': '<3',
        '\u00bb': '>>',
        '\u00ab': '<<',
        '\u00ae': '(R)',
        '\u00a9': '(C)',
        '\u2122': '(TM)',
        '\u00b1': '+/-',
        '\u00d7': 'x',
        '\u00f7': '/',
        '\u03b1': 'alpha',
        '\u03b2': 'beta',
    }
    for ch, rep in replacements.items():
        text = text.replace(ch, rep)
    # fallback para qualquer restante fora do latin-1
    return text.encode('latin-1', errors='replace').decode('latin-1')

MD_FILE  = "documentacao_tecnica.md"
PDF_FILE = "documentacao_tecnica.pdf"

# ── Cores (RGB) ───────────────────────────────────────────────────
C_TITLE    = (15,  23,  42)   # azul-escuro
C_H1       = (30,  64, 175)   # azul forte
C_H2       = (37,  99, 235)   # azul médio
C_H3       = (59, 130, 246)   # azul claro
C_TEXT     = (30,  41,  59)   # cinza-azul
C_CODE_BG  = (241, 245, 249)  # fundo cinza claro
C_CODE_TXT = (51,  65,  85)   # texto cinza
C_TABLE_H  = (30,  64, 175)   # cabeçalho tabela
C_TABLE_R1 = (248, 250, 252)  # linha par
C_TABLE_R2 = (255, 255, 255)  # linha ímpar
C_BORDER   = (203, 213, 225)  # borda


class DocPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_H2)
        self.cell(0, 8, _safe("MilkShow -- Documentacao Tecnica"), align="L")
        self.cell(0, 8, _safe(f"Pagina {self.page_no()}"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C_BORDER)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*C_BORDER)
        self.cell(0, 6, _safe("MilkShow (C) 2026 -- Frederico Martins"), align="C")


def make_cover(pdf):
    pdf.add_page()
    # fundo escuro simulado com retângulo
    pdf.set_fill_color(*C_TITLE)
    pdf.rect(0, 0, pdf.w, 90, "F")

    pdf.set_y(22)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "MilkShow", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(147, 197, 253)
    pdf.cell(0, 8, _safe("Documentacao Tecnica do Sistema"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(95)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_TEXT)

    meta = [
        ("Versao",      "1.0"),
        ("Data",        "Maio de 2026"),
        ("Autor",       "Frederico Martins"),
        ("Repositorio", "github.com/fredmartins12/MilkShow"),
    ]
    for label, val in meta:
        pdf.set_x(pdf.l_margin + 30)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, val, new_x="LMARGIN", new_y="NEXT")


def strip_inline(text):
    """Remove marcacao markdown inline basica para texto limpo."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    return _safe(text)


def bold_parts(pdf, line, font_size):
    """Escreve linha com partes em negrito (**texto**)."""
    parts = re.split(r'(\*\*[^*]+\*\*)', line)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            pdf.set_font("Helvetica", "B", font_size)
            pdf.write(5, _safe(part[2:-2]))
        else:
            part = re.sub(r'`([^`]+)`', r'\1', part)
            part = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', part)
            pdf.set_font("Helvetica", "", font_size)
            pdf.write(5, _safe(part))


def render_table(pdf, rows):
    """Renderiza tabela markdown."""
    if len(rows) < 2:
        return
    header = rows[0]
    data   = rows[2:]  # skip separator

    cols = [c.strip() for c in header.strip('|').split('|')]
    n = len(cols)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = usable / n

    # cabeçalho
    pdf.set_fill_color(*C_TABLE_H)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_draw_color(*C_BORDER)
    for col in cols:
        pdf.cell(col_w, 7, strip_inline(col)[:40], border=1, fill=True)
    pdf.ln()

    # linhas
    for i, row in enumerate(data):
        cells = [c.strip() for c in row.strip('|').split('|')]
        # equalize
        while len(cells) < n:
            cells.append("")
        fill_color = C_TABLE_R1 if i % 2 == 0 else C_TABLE_R2
        pdf.set_fill_color(*fill_color)
        pdf.set_text_color(*C_TEXT)
        pdf.set_font("Helvetica", "", 7.5)

        # calcula altura necessária para a linha mais alta
        max_h = 6
        for cell in cells[:n]:
            txt = strip_inline(cell)[:120]
            lines_needed = max(1, len(txt) // max(1, int(col_w / 2.1)))
            if lines_needed > 1:
                max_h = max(max_h, 5 * lines_needed)

        x0 = pdf.get_x()
        y0 = pdf.get_y()
        for j, cell in enumerate(cells[:n]):
            txt = strip_inline(cell)[:120]
            pdf.set_xy(x0 + j * col_w, y0)
            pdf.multi_cell(col_w, 5, txt, border=1, fill=True)
        pdf.set_xy(x0, y0 + max_h)

    pdf.ln(3)


def render_code(pdf, lines):
    """Renderiza bloco de código."""
    pdf.set_fill_color(*C_CODE_BG)
    pdf.set_draw_color(*C_BORDER)
    pdf.set_text_color(*C_CODE_TXT)
    pdf.set_font("Courier", "", 7)
    pdf.set_x(pdf.l_margin)
    text = _safe("\n".join(lines))
    pdf.multi_cell(
        pdf.w - pdf.l_margin - pdf.r_margin, 4.5,
        text, border=1, fill=True, new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(3)


def parse_and_render(pdf, md_text):
    lines = md_text.split("\n")
    i = 0
    table_buf = []
    code_buf  = []
    in_code   = False

    while i < len(lines):
        line = lines[i]

        # ── bloco de código ─────────────────────────────────────────
        if line.startswith("```"):
            if in_code:
                render_code(pdf, code_buf)
                code_buf = []
                in_code  = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # ── tabela ──────────────────────────────────────────────────
        if line.startswith("|"):
            table_buf.append(line)
            i += 1
            continue
        elif table_buf:
            render_table(pdf, table_buf)
            table_buf = []

        # ── headings ────────────────────────────────────────────────
        if line.startswith("# ") and not line.startswith("## "):
            txt = strip_inline(line[2:])
            # Seção principal — nova página
            pdf.add_page()
            pdf.set_fill_color(*C_H1)
            pdf.rect(pdf.l_margin - 5, pdf.get_y() - 2, pdf.w - pdf.l_margin - pdf.r_margin + 10, 12, "F")
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 10, txt, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*C_TEXT)
            pdf.ln(4)

        elif line.startswith("## "):
            txt = strip_inline(line[3:])
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*C_H2)
            pdf.set_fill_color(219, 234, 254)
            pdf.cell(0, 8, "  " + txt, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*C_TEXT)
            pdf.ln(2)

        elif line.startswith("### "):
            txt = strip_inline(line[4:])
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*C_H3)
            pdf.cell(0, 7, txt, new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(*C_H3)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 60, pdf.get_y())
            pdf.set_text_color(*C_TEXT)
            pdf.ln(2)

        elif line.startswith("#### "):
            txt = strip_inline(line[5:])
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*C_TEXT)
            pdf.cell(0, 6, txt, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        # ── divisor ─────────────────────────────────────────────────
        elif line.strip() in ("---", "***", "___"):
            pdf.set_draw_color(*C_BORDER)
            pdf.ln(2)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)

        # ── lista com bullet ────────────────────────────────────────
        elif re.match(r'^(\s*)[-*+] ', line):
            indent = len(line) - len(line.lstrip())
            txt = strip_inline(re.sub(r'^(\s*)[-*+] ', '', line))
            bullet = "*" if indent == 0 else "-"
            x_off = pdf.l_margin + indent * 2
            pdf.set_x(x_off)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*C_TEXT)
            pdf.cell(5, 5, bullet)
            pdf.multi_cell(pdf.w - x_off - pdf.r_margin - 5, 5, txt)

        # ── lista numerada ──────────────────────────────────────────
        elif re.match(r'^\d+\. ', line):
            num  = re.match(r'^(\d+)\. ', line).group(1)
            txt  = strip_inline(re.sub(r'^\d+\. ', '', line))
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*C_TEXT)
            pdf.cell(7, 5, num + ".")
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 7, 5, txt)

        # ── linha em branco ─────────────────────────────────────────
        elif line.strip() == "":
            pdf.ln(2)

        # ── parágrafo normal ────────────────────────────────────────
        else:
            if line.strip():
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*C_TEXT)
                bold_parts(pdf, line, 9)
                pdf.ln()

        i += 1

    # flush pendentes
    if table_buf:
        render_table(pdf, table_buf)
    if in_code and code_buf:
        render_code(pdf, code_buf)


def main():
    with open(MD_FILE, encoding="utf-8") as f:
        md_text = f.read()

    pdf = DocPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=18, top=18, right=18)

    make_cover(pdf)
    parse_and_render(pdf, md_text)

    pdf.output(PDF_FILE)
    print(f"PDF gerado: {PDF_FILE}")


if __name__ == "__main__":
    main()
