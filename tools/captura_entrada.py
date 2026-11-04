import sys
from playwright.sync_api import sync_playwright
url,out=sys.argv[1],sys.argv[2]
import os; os.makedirs(out,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch()
    for n,(w,h) in {"movil-390x844":(390,844),"escritorio-1280x800":(1280,800),"escritorio-1920x1080":(1920,1080),"escritorio-1024x768":(1024,768)}.items():
        pg=b.new_page(viewport={"width":w,"height":h},device_scale_factor=2 if w<500 else 1)
        errs=[];pg.on("console",lambda m:errs.append(m.text) if m.type=="error" else None)
        pg.goto(url);pg.wait_for_load_state("networkidle");pg.wait_for_timeout(800)
        r=pg.evaluate("(()=>{const i=document.querySelector('.intro__foto img').getBoundingClientRect();const n=document.querySelector('.intro__foto img');return [i.x,i.y,i.width,i.height,n.currentSrc,innerWidth,innerHeight]})()")
        bt=pg.evaluate("JSON.stringify(document.querySelector('#btnIngresar').getBoundingClientRect())")
        pg.screenshot(path=f"{out}/entrada-{n}.png"); print(n,r,bt,errs)
