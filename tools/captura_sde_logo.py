import sys,os
from playwright.sync_api import sync_playwright
url,out=sys.argv[1].rstrip("/"),sys.argv[2]; os.makedirs(out,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":390,"height":844},device_scale_factor=2); errs=[]
    pg.on("console",lambda m:errs.append(m.text) if m.type=="error" else None)
    pg.goto(url+"/?p=sde"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800); pg.screenshot(path=f"{out}/sde-movil-entrada.png")
    pg.click("#btnIngresar"); pg.wait_for_selector("body[data-listo]"); pg.wait_for_timeout(3000); pg.screenshot(path=f"{out}/sde-movil-plano.png")
    pg.evaluate("Masterplan.abrirLote('E2-M5-L1')"); pg.wait_for_timeout(700); pg.screenshot(path=f"{out}/sde-movil-tarjeta.png")
    pg.goto(url+"/?p=sde"); pg.wait_for_load_state("networkidle"); pg.click(".proy-tabs--intro .proy-tab[href*='p=pde']"); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800)
    pg.screenshot(path=f"{out}/pde-movil-entrada-tras-cambio.png"); print(errs, pg.url)
