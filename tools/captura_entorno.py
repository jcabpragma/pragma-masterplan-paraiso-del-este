import sys,os
from playwright.sync_api import sync_playwright
url,out=sys.argv[1].rstrip("/"),sys.argv[2]; os.makedirs(out,exist_ok=True)
V=[("sde","1-alejado",19.198,-70.4885,16.25),("sde","2-galpones-sur-z19",19.1935,-70.4895,19),("sde","3-galpones-este-z19",19.1995,-70.4848,19),
   ("sde","4-borde-z18",19.1975,-70.4880,18),("pde","1-plano",None,None,None),("pde","2-borde-z18",None,None,18)]
with sync_playwright() as p:
    b=p.chromium.launch()
    for pr,nom,la,lo,z in V:
        pg=b.new_page(viewport={"width":390,"height":844},device_scale_factor=2); errs=[]
        pg.on("console",lambda m:errs.append(m.text) if m.type=="error" else None)
        pg.goto(f"{url}/?p={pr}&ver=plano"); pg.wait_for_selector("body[data-listo]"); pg.wait_for_timeout(1500)
        if z and la: pg.evaluate(f"Masterplan.mapa().setView([{la},{lo}],{z},{{animate:false}})")
        elif z: pg.evaluate(f"var m=Masterplan.mapa();m.setZoom({z},{{animate:false}});m.panBy([150,150],{{animate:false}})")
        pg.wait_for_timeout(3500); pg.screenshot(path=f"{out}/{pr}-movil-{nom}.png")
        print(pr,nom,pg.evaluate("document.querySelectorAll('path.lote').length"),errs); pg.close()
