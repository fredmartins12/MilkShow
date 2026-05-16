# -*- coding: utf-8 -*-
"""
Gera MilkShow_Pitch_CentelhaPB.pdf
Captura cada slide do pitch.html via Playwright e monta PDF com fpdf2.

Uso:
    py -3 docs/gerar_pitch_pdf.py
"""
import asyncio, os, sys, threading, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from fpdf import FPDF

# forcar UTF-8 no stdout do Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT         = Path(__file__).parent.parent
DOCS         = Path(__file__).parent
OUT_PDF      = DOCS / "MilkShow_Pitch_CentelhaPB.pdf"
TMP_DIR      = DOCS / "_slides_tmp"
PORT         = 8765
TOTAL_SLIDES = 12
W, H         = 1920, 1080

class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def start_server():
    os.chdir(ROOT)
    srv = HTTPServer(("127.0.0.1", PORT), SilentHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def capturar_slides():
    from playwright.async_api import async_playwright

    TMP_DIR.mkdir(exist_ok=True)
    url = f"http://127.0.0.1:{PORT}/docs/pitch.html"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page(viewport={"width": W, "height": H})

        print(f"  -> Abrindo {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2.5)

        paths = []
        for i in range(TOTAL_SLIDES):
            # No slide 12 (último), aguarda o QR code carregar
            if i == TOTAL_SLIDES - 1:
                try:
                    await page.wait_for_selector(
                        "#qrImg[src]:not([src=''])",
                        timeout=8000
                    )
                    # aguarda a imagem renderizar de fato
                    await page.wait_for_function(
                        "document.getElementById('qrImg')?.complete && "
                        "document.getElementById('qrImg')?.naturalWidth > 0",
                        timeout=8000
                    )
                    await asyncio.sleep(0.5)
                except Exception:
                    print("  ! QR code nao carregou a tempo, capturando mesmo assim")

            path = TMP_DIR / f"slide_{i+1:02d}.png"
            await page.screenshot(path=str(path), full_page=False)
            paths.append(path)
            print(f"  -> Slide {i+1:02d}/{TOTAL_SLIDES}")

            if i < TOTAL_SLIDES - 1:
                await page.keyboard.press("ArrowRight")
                await asyncio.sleep(0.7)

        await browser.close()
    return paths

def montar_pdf(paths):
    pdf = FPDF(orientation="L", unit="mm", format=(108, 192))
    pdf.set_auto_page_break(False)
    pdf.set_margins(0, 0, 0)

    for path in paths:
        pdf.add_page()
        pdf.image(str(path), x=0, y=0, w=192, h=108)

    pdf.output(str(OUT_PDF))
    size_kb = OUT_PDF.stat().st_size // 1024
    print(f"\n  PDF gerado: {OUT_PDF}")
    print(f"  {len(paths)} slides | {size_kb} KB")

def main():
    print("\nMilkShow -- Gerador de Pitch PDF")
    print("=" * 45)

    print("\n[1/3] Servidor local na porta", PORT)
    srv = start_server()
    time.sleep(0.5)

    print(f"[2/3] Capturando {TOTAL_SLIDES} slides ({W}x{H})...")
    paths = asyncio.run(capturar_slides())

    print("\n[3/3] Montando PDF...")
    montar_pdf(paths)

    for p in paths:
        p.unlink(missing_ok=True)
    try:
        TMP_DIR.rmdir()
    except Exception:
        pass

    srv.shutdown()

    print("\nPronto! Arquivo salvo em docs/")
    os.startfile(str(DOCS))

if __name__ == "__main__":
    main()
