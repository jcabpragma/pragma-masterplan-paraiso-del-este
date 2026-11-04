"""Une el inventario de SIGI (CSV) con los lotes del plano por código de lote.

Uso:  python3 tools/merge_inventario.py /ruta/inventario.csv [pde|sde]
CSV esperado: lote,manzana,m2,precio,estado,etiquetas   (lote = E1-M1-L3)

Salidas:
  data/inventario.json        PÚBLICO. estado, m², tipología. **Nunca incluye precio.**
  privado/precios.json        PRIVADO (no se sube al repo, ver .gitignore). Precio RD$/m² por lote.
  privado/reporte_merge.json  Coincidencias y diferencias con el plano.

Estados: disponible | reservado | vendido | no_disponible  (bloqueado -> no_disponible).
"""
import sys, os, csv, json, re
base = os.path.dirname(os.path.abspath(__file__)) + "/.."
src = sys.argv[1] if len(sys.argv) > 1 else "/workspace/paraiso/inventario_pde.csv"
proy = sys.argv[2] if len(sys.argv) > 2 else "pde"
NOMBRE = {"pde": "Paraíso del Este", "sde": "Samanes del Este"}[proy]
suf = "" if proy == "pde" else "_" + proy
os.makedirs(f"{base}/privado", exist_ok=True)

def norm(c):
    m = re.match(r"^\s*E?(\d+)\s*-\s*M?(\d+)\s*-\s*L?(\d+)\s*$", c, re.I)
    return f"E{int(m.group(1))}-M{int(m.group(2))}-L{int(m.group(3))}" if m else c.strip()
ESTADOS = {"disponible": "disponible", "reservado": "reservado", "vendido": "vendido",
           "no_disponible": "no_disponible", "no disponible": "no_disponible", "bloqueado": "no_disponible"}

geo = json.load(open(f"{base}/proyectos/{proy}/data/lots.geojson"))
plano = {f["properties"]["codigo"]: f["properties"] for f in geo["features"]}
inv, precios, sin_estado = {}, {}, []
for r in csv.DictReader(open(src, encoding="utf-8-sig")):
    c = norm(r["lote"]); est = ESTADOS.get(r["estado"].strip().lower())
    if est is None: sin_estado.append((c, r["estado"])); est = "no_disponible"
    tip = [t.strip().capitalize() for t in re.split(r"[;,|]", r.get("etiquetas", "")) if t.strip()]
    inv[c] = {"estado": est, "estado_sigi": r["estado"].strip().lower(), "m2": round(float(r["m2"].replace(",", "")), 2), "tipologia": tip}
    p = re.sub(r"[^\d.]", "", r.get("precio", "") or "")
    if p: precios[c] = {"precio_m2": float(p), "moneda": "RD$"}

coinciden = sorted(set(inv) & set(plano))
solo_plano = sorted(set(plano) - set(inv)); solo_sigi = sorted(set(inv) - set(plano))
publico = {"proyecto": NOMBRE, "fuente": "SIGI", "lotes": {}}
for c in coinciden:
    v = inv[c]; publico["lotes"][c] = {"estado": v["estado"], "m2": v["m2"], "tipologia": v["tipologia"]}
json.dump(publico, open(f"{base}/proyectos/{proy}/data/inventario.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"aviso": "PRIVADO - lista en borrador, no publicar", "lotes": precios}, open(f"{base}/privado/precios{suf}.json", "w"), ensure_ascii=False, indent=0)
dif_m2 = [(c, plano[c]["m2_dxf"], inv[c]["m2"]) for c in coinciden if abs(plano[c]["m2_dxf"] - inv[c]["m2"]) > 1]
rep = {"plano": len(plano), "sigi": len(inv), "coinciden": len(coinciden),
       "solo_plano": solo_plano, "solo_sigi": solo_sigi, "estados_desconocidos": sin_estado,
       "m2_distintos_mas_1m2": len(dif_m2), "ejemplos_m2_distintos": dif_m2[:10]}
json.dump(rep, open(f"{base}/privado/reporte_merge{suf}.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: rep[k] for k in ("plano", "sigi", "coinciden", "solo_plano", "solo_sigi", "m2_distintos_mas_1m2")}, ensure_ascii=False, indent=1))
