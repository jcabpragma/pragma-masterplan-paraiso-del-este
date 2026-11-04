import sys,os
from playwright.sync_api import sync_playwright
url,out=sys.argv[1].rstrip("/"),sys.argv[2]; os.makedirs(out,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch()
    for n,(w,h) in {"movil":(390,844),"escritorio":(1280,800)}.items():
        pg=b.new_page(viewport={"width":w,"height":h}); errs=[]
        pg.on("console",lambda m:errs.append(m.text) if m.type=="error" else None)
        pg.goto(url+"/?p=sde"); pg.wait_for_load_state("networkidle"); pg.screenshot(path=f"{out}/sde-{n}-entrada.png")
        pg.click("#btnIngresar"); pg.wait_for_selector("body[data-listo]"); pg.wait_for_timeout(2500)
        pg.screenshot(path=f"{out}/sde-{n}-plano.png")
        n_l=pg.evaluate("document.querySelectorAll('path.lote').length")
        pg.evaluate("Masterplan.abrirLote('E2-M5-L1')"); pg.wait_for_timeout(600)
        card=pg.inner_text("#card"); wa=pg.get_attribute("#btnWA","href")
        pg.screenshot(path=f"{out}/sde-{n}-tarjeta.png")
        pg.click(".topbar .proy-tab[href*='p=pde']"); pg.wait_for_selector("body[data-listo]"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{out}/switch-{n}-a-pde.png")
        print(n,n_l,repr(card[:120]),wa,"RD$" in pg.content(),errs,pg.url)
