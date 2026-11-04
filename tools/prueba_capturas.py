"""Prueba con Playwright: capturas, tap real sobre un lote y verificación del link de WhatsApp.
Uso: python3 tools/prueba_capturas.py [URL] [carpeta_salida] [codigo_lote]
Local: python3 -m http.server 8765  ->  python3 tools/prueba_capturas.py http://localhost:8765/ screenshots/local"""
import sys, json, os, urllib.parse
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
OUT = sys.argv[2] if len(sys.argv) > 2 else "screenshots/local"
LOTE = sys.argv[3] if len(sys.argv) > 3 else "E1-M1-L3"
os.makedirs(OUT, exist_ok=True)
res = {"url": URL, "lote": LOTE}

def acercar(pg, codigo, z=19):
    pg.evaluate("""([c,z]) => { const M = window.Masterplan, f = M.lotes().find(x => x.properties.codigo === c);
        const pts = f.geometry.coordinates[0]; const lat = pts.reduce((a,p)=>a+p[1],0)/pts.length, lng = pts.reduce((a,p)=>a+p[0],0)/pts.length;
        M.mapa().setView([lat, lng], z, {animate:false}); }""", [codigo, z])
    pg.wait_for_timeout(1500)

with sync_playwright() as p:
    b = p.chromium.launch()
    errs = []
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto(URL); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
    pg.screenshot(path=f"{OUT}/01-movil-entrada.png")
    pg.tap("#btnIngresar")
    pg.wait_for_selector("body[data-listo='1']"); pg.wait_for_timeout(2500)
    res["lotes_dibujados"] = pg.locator("path.lote").count()
    # ¿la vista inicial encuadra todo el proyecto?
    res["movil_vista_contiene_todo"] = pg.evaluate("""() => { const m = window.Masterplan.mapa(); const b = L.latLngBounds([]); window.Masterplan.lotes().forEach(f => f.geometry.coordinates[0].forEach(c => b.extend([c[1], c[0]]))); return m.getBounds().contains(b); }""")
    pg.screenshot(path=f"{OUT}/02-movil-plano.png")
    acercar(pg, LOTE)
    box = pg.locator(f"path.lote[data-codigo='{LOTE}']").bounding_box()
    pg.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.wait_for_selector("#card:not([hidden])"); pg.wait_for_timeout(500)
    res["card_titulo"] = pg.inner_text("#cardCodigo")
    res["card_texto"] = pg.inner_text("#cardBody")
    res["whatsapp_href"] = pg.get_attribute("#btnWA", "href")
    pg.screenshot(path=f"{OUT}/03-movil-tarjeta-lote.png")
    pg.tap("#btnFicha"); pg.wait_for_selector("#ficha:not([hidden])"); pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/04-movil-ficha-lote.png")
    pg.click("#ficha .card__close"); pg.tap("#card .card__close")
    pg.tap(".chip[data-etapa='E1']"); pg.wait_for_timeout(1200)
    pg.tap(".chip[data-estado='disponible']"); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{OUT}/05-movil-filtro-etapa1-disponibles.png")
    ctx.close()
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_load_state("networkidle")
    pg.click("#btnIngresar"); pg.wait_for_selector("body[data-listo='1']"); pg.wait_for_timeout(2500)
    pg.screenshot(path=f"{OUT}/06-escritorio-plano.png")
    acercar(pg, LOTE, 18.5)
    box = pg.locator(f"path.lote[data-codigo='{LOTE}']").bounding_box()
    pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.wait_for_selector("#card:not([hidden])"); pg.wait_for_timeout(400)
    res["desktop_card"] = pg.inner_text("#cardCodigo"); res["desktop_wa"] = pg.get_attribute("#btnWA", "href")
    pg.screenshot(path=f"{OUT}/07-escritorio-tarjeta-lote.png")
    res["html_contiene_RD$"] = "RD$" in pg.content()
    b.close()
res["errores_js"] = errs
res["wa_contiene_codigo"] = LOTE in urllib.parse.unquote(res["whatsapp_href"]) and LOTE in urllib.parse.unquote(res["desktop_wa"])
res["wa_numero_ok"] = res["whatsapp_href"].startswith("https://wa.me/18297623117")
print(json.dumps(res, ensure_ascii=False, indent=1))
