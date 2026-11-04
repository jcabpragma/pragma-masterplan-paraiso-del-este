"""Capturas extra PDE v7: vista media con pines de áreas verdes, lotes reales de cerca y ficha (sin nota referencial)."""
import sys, os
from playwright.sync_api import sync_playwright
url, out = sys.argv[1].rstrip("/"), sys.argv[2]; os.makedirs(out, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for n, (w, h) in {"movil": (390, 844), "escritorio": (1280, 800)}.items():
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if n == "movil" else 1); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(url + "/?p=pde"); pg.wait_for_load_state("networkidle")
        pg.click("#btnIngresar"); pg.wait_for_selector("body[data-listo]"); pg.wait_for_timeout(2500)
        pg.evaluate("Masterplan.mapa().setView([18.5462,-69.8115],17,{animate:false})"); pg.wait_for_timeout(2500)
        pg.screenshot(path=f"{out}/pde-{n}-areas-verdes.png")
        pines = pg.evaluate("[...document.querySelectorAll('.amenity-pin')].filter(e=>e.offsetParent).length")
        pg.evaluate("Masterplan.mapa().setView([18.5470,-69.8090],18.6,{animate:false})"); pg.wait_for_timeout(2500)
        pg.screenshot(path=f"{out}/pde-{n}-lotes-cerca.png")
        pg.evaluate("Masterplan.abrirLote('E2-M22-L5')"); pg.wait_for_timeout(1200)
        pg.screenshot(path=f"{out}/pde-{n}-tarjeta-E2-M22-L5.png")
        pg.click("#btnFicha"); pg.wait_for_selector("#ficha:not([hidden])"); pg.wait_for_timeout(400)
        ficha = pg.inner_text("#fichaBody"); pg.screenshot(path=f"{out}/pde-{n}-ficha-E2-M22-L5.png")
        print(n, "pines visibles z17:", pines, "| nota referencial:", "referencial" in ficha, "| RD$:", "RD$" in pg.content(), "| errores:", errs)
