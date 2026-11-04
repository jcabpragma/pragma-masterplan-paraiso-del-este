import sys,os
from playwright.sync_api import sync_playwright
url,out=sys.argv[1].rstrip("/"),sys.argv[2]; os.makedirs(out,exist_ok=True)
# zonas de galpones SDE (sur y este) para comprobar el difuminado al acercar
VIS={"sde":[("galpones-sur",19.1955,-70.4905,18.5),("galpones-este",19.2015,-70.4855,18.5),("galpones-este-z20",19.2015,-70.4855,20),("galpones-sur-z20",19.1955,-70.4905,20)],
     "pde":[("borde-z18",None,None,18)]}
with sync_playwright() as p:
    b=p.chromium.launch()
    for n,(w,h) in {"movil":(390,844),"escritorio":(1280,800)}.items():
        for pr in ("sde","pde"):
            pg=b.new_page(viewport={"width":w,"height":h},device_scale_factor=2 if n=="movil" else 1); errs=[]
            pg.on("console",lambda m:errs.append(m.text) if m.type=="error" else None)
            pg.goto(f"{url}/?p={pr}&ver=plano"); pg.wait_for_selector("body[data-listo]"); pg.wait_for_timeout(3000)
            pg.screenshot(path=f"{out}/{pr}-{n}-1-plano.png")
            pg.evaluate("Masterplan.mapa().zoomIn(1)")
            pg.wait_for_timeout(2000); pg.screenshot(path=f"{out}/{pr}-{n}-2-zoom.png")
            pg.mouse.move(w/2,h/2); pg.mouse.down(); pg.mouse.move(w/2-w*0.3,h/2-h*0.25,steps=12); pg.mouse.up()
            pg.wait_for_timeout(2500); pg.screenshot(path=f"{out}/{pr}-{n}-3-pan.png")
            for nom,la,lo,z in VIS[pr]:
                if la is None: continue
                pg.evaluate(f"Masterplan.mapa().setView([{la},{lo}],{z},{{animate:false}})"); pg.wait_for_timeout(3000)
                pg.screenshot(path=f"{out}/{pr}-{n}-{nom}.png")
            n_l=pg.evaluate("document.querySelectorAll('path.lote').length")
            print(pr,n,n_l,pg.evaluate("getComputedStyle(document.querySelector('.leaflet-nitido-pane')||document.body).clipPath.slice(0,40)"),errs)
            pg.close()
