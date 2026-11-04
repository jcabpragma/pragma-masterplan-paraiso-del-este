"""v8: prueba del selector Satélite | Mapa en PDE y SDE (móvil 390x844 y escritorio 1280x800).
Uso: python3 tools/captura_v8_fondo.py URL CARPETA_SALIDA"""
import sys, os
from playwright.sync_api import sync_playwright
url, out = sys.argv[1].rstrip("/"), sys.argv[2]; os.makedirs(out, exist_ok=True)
LOTE = {"pde": "E2-M22-L5", "sde": "E2-M5-L1"}
CAJA = "(s=>{const e=document.querySelector(s); if(!e||!e.offsetParent) return null; const r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]})"
def cruza(a, b): return bool(a and b and a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])
fallos = []
with sync_playwright() as p:
    br = p.chromium.launch()
    for n, (w, h) in {"movil": (390, 844), "escritorio": (1280, 800)}.items():
        for proy in ("pde", "sde"):
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if n == "movil" else 1)
            pg = ctx.new_page(); errs, teselas_mal = [], []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("response", lambda r: teselas_mal.append(r.url) if r.status >= 400 and ("openstreetmap" in r.url or "arcgisonline" in r.url) else None)
            pg.goto(url + "/?p=" + proy); pg.wait_for_load_state("networkidle")
            pg.click("#btnIngresar"); pg.wait_for_selector("body[data-listo='1']"); pg.wait_for_timeout(2500)
            ini = pg.get_attribute(".fondo-sel button[aria-pressed='true']", "data-fondo")
            pg.screenshot(path=f"{out}/{proy}-{n}-satelite.png")
            pg.click(".fondo-sel button[data-fondo='mapa']"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2000)
            pg.screenshot(path=f"{out}/{proy}-{n}-mapa.png")
            atrib = pg.inner_text(".leaflet-control-attribution")
            sel = pg.evaluate(CAJA + "('.fondo-sel')")
            choques = {s: cruza(sel, pg.evaluate(CAJA + f"('{s}')")) for s in ("#filtros", "#filtrosEtapa", ".leaflet-control-zoom", "#leyenda", ".leaflet-control-attribution")}
            # zoom máximo: sin teselas en blanco
            pg.evaluate(f"(()=>{{const m=Masterplan.mapa(), l=Masterplan.lotes().find(f=>f.properties.codigo==='{LOTE[proy]}')||Masterplan.lotes()[0]; const c=L.polygon(l.geometry.coordinates[0].map(c=>[c[1],c[0]])).getBounds().getCenter(); m.setView(c,m.getMaxZoom(),{{animate:false}})}})()")
            pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(2000)
            zmax = pg.evaluate("Masterplan.mapa().getZoom()")
            pg.screenshot(path=f"{out}/{proy}-{n}-mapa-zoom-max.png")
            pg.evaluate("Masterplan.mapa().setZoom(18,{animate:false})"); pg.wait_for_timeout(1500)
            pg.evaluate(f"Masterplan.abrirLote('{LOTE[proy]}')"); pg.wait_for_timeout(1200)
            choque_card = cruza(pg.evaluate(CAJA + "('.fondo-sel')"), pg.evaluate(CAJA + "('#card')"))
            pg.screenshot(path=f"{out}/{proy}-{n}-mapa-tarjeta.png")
            pg.reload(); pg.wait_for_load_state("networkidle"); pg.click("#btnIngresar"); pg.wait_for_selector("body[data-listo='1']"); pg.wait_for_timeout(1500)
            recordado = pg.get_attribute(".fondo-sel button[aria-pressed='true']", "data-fondo")
            pg.click(".fondo-sel button[data-fondo='satelite']"); pg.wait_for_timeout(1500)
            vuelta = pg.evaluate("document.getElementById('map').classList.contains('fondo-mapa')")
            html = pg.content()
            r = dict(inicio=ini, recordado=recordado, vuelve_satelite=not vuelta, zoom_max=zmax, choques=choques, choque_tarjeta=choque_card,
                     atribucion=atrib.replace("\n", " "), teselas_error=len(teselas_mal), errores_js=errs, rd=("RD$" in html))
            print(proy, n, r)
            if ini != "satelite" or recordado != "mapa" or vuelta or any(choques.values()) or choque_card or errs or teselas_mal: fallos.append((proy, n))
            ctx.close()
    br.close()
print("FALLOS:", fallos or "ninguno")
