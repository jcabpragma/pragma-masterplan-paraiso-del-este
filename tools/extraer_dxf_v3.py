"""PDE v3: lotes REALES desde el DXF completo de Paraíso del Este (recibido 2026-11-04, 29.8 MB, termina en EOF).

Uso:  python3 tools/extraer_dxf_v3.py /ruta/plano_pde.dxf
Salida (proyectos/pde/data/): lots.geojson, manzanas.json, limite.json, mascara.json, amenidades.json
       privado/lots_v3_utm.geojson, privado/reporte_extraccion_v3.json

Contenido del DXF: todo en la capa 0 (dibujo explotado). Rótulos de parcela = MTEXT
  "01-05-3\\n224.15\\nHabitacional\\nEtapa: 1" -> E{etapa}-M{manzana}-L{lote}  (1.379 rótulos, sin repetidos)
Linderos = LINE + LWPOLYLINE + ARC de la capa 0. Método (igual que SDE: rótulo dentro de polígono):
 1. polygonize() de todas las líneas -> caras cerradas.
 2. Cada rótulo toma la cara más pequeña que lo contiene; se acepta si su área = m² del rótulo ±5 %  -> "real".
 3. Cara partida por una línea ajena (área < m²): se une con caras vecinas sin rótulo hasta llegar al m² -> "real".
 4. Cara compartida por 2+ rótulos (falta el lindero en el DXF): se corta paralelo al lindero vecino,
    en la posición que da el m² de cada rótulo -> "ajustada" (la ficha muestra "contorno referencial").
Límite del proyecto = LWPOLYLINE cerrada de 51,4 ha que contiene los 1.379 rótulos.
Amenidades = rótulos "AV-PARQUE nn" (áreas verdes) de 2.000 m² o más.
Coordenadas UTM 19N (EPSG:32619, $INSUNITS=6 m) -> WGS84.
"""
import sys, os, re, json, collections
import numpy as np, ezdxf
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import polygonize, unary_union, transform
from shapely.strtree import STRtree
from shapely import affinity
from pyproj import Transformer

src = sys.argv[1]
base = os.path.dirname(os.path.abspath(__file__)) + "/.."
out = f"{base}/proyectos/pde/data"; os.makedirs(f"{base}/privado", exist_ok=True)
doc = ezdxf.readfile(src); msp = doc.modelspace()

labs, otros = [], []
for e in msp.query("MTEXT"):
    pr = [p.strip() for p in e.plain_text().split("\n")]
    m = re.match(r"^(\d+)-(\d+)-(\d+)$", pr[0])
    xy = (e.dxf.insert.x, e.dxf.insert.y)
    if m and len(pr) >= 4:
        et = int(re.sub(r"\D", "", pr[3]))
        labs.append(dict(codigo=f"E{et}-M{int(m.group(2))}-L{int(m.group(3))}", etiqueta_dxf=pr[0], etapa=f"E{et}",
                         manzana=int(m.group(2)), lote=int(m.group(3)), m2_dxf=float(pr[1].replace(",", "")), uso_dxf=pr[2], xy=xy))
    else:
        otros.append((pr, xy))
assert len(set(l["codigo"] for l in labs)) == len(labs)

segs = []
for e in msp.query("LINE"):
    a, b = e.dxf.start, e.dxf.end
    if (a - b).magnitude > 1e-6: segs.append(LineString([(a.x, a.y), (b.x, b.y)]))
perim = None
for e in msp.query("LWPOLYLINE"):
    pts = [p[:2] for p in e.get_points()]
    if e.closed and len(pts) > 2:
        pg = Polygon(pts)
        if pg.area > 400000: perim = pg
        pts = pts + [pts[0]]
    if len(pts) > 1: segs.append(LineString(pts))
for e in msp.query("ARC"):
    segs.append(LineString([(p.x, p.y) for p in e.flattening(0.05)]))
caras = list(polygonize(unary_union(segs))); tree = STRtree(caras)
lab_pts = [Point(l["xy"]) for l in labs]
con_rotulo = collections.defaultdict(list)
def cara_de(i):
    hit = [k for k in tree.query(lab_pts[i]) if caras[k].contains(lab_pts[i])]
    return min(hit, key=lambda k: caras[k].area) if hit else None
for i in range(len(labs)):
    k = cara_de(i); labs[i]["cara"] = k
    if k is not None: con_rotulo[k].append(i)

geom, metodo = {}, {}
# 2 + 3
for i, l in enumerate(labs):
    k = l["cara"]
    if k is None or len(con_rotulo[k]) > 1: continue
    g = caras[k]; r = g.area / l["m2_dxf"]
    if 0.95 < r < 1.05: geom[i] = g; metodo[i] = "real"; continue
    if r < 0.95:
        usadas = {k}
        for _ in range(4):
            cand = [j for j in tree.query(g.buffer(0.05)) if j not in usadas and j not in con_rotulo
                    and caras[j].intersection(g.buffer(0.05)).area > 0.05 and caras[j].area < l["m2_dxf"]]
            mejor = min(cand, key=lambda j: abs(g.area + caras[j].area - l["m2_dxf"]), default=None)
            if mejor is None or abs(g.area + caras[mejor].area - l["m2_dxf"]) >= abs(g.area - l["m2_dxf"]): break
            g = unary_union([g, caras[mejor]]).buffer(0.01).buffer(-0.01); usadas.add(mejor)
            if 0.98 < g.area / l["m2_dxf"] < 1.02: break
        if 0.95 < g.area / l["m2_dxf"] < 1.05 and g.geom_type == "Polygon": geom[i] = g; metodo[i] = "real"

# 4: caras con varios rótulos
def cortar(poly, ids):
    P = np.array([labs[i]["xy"] for i in ids]); c = P.mean(0)
    u = P[-1] - P[0]; u = u / np.linalg.norm(u)
    # lindero vecino: arista larga del polígono más perpendicular a u
    xy = np.array(poly.exterior.coords); best, bl = None, 0
    for a, b in zip(xy[:-1], xy[1:]):
        d = b - a; n = np.linalg.norm(d)
        if n > 5 and abs(d @ u) / n < 0.35 and n > bl: best, bl = d / n, n
    v = best if best is not None else np.array([-u[1], u[0]])
    nrm = np.array([-v[1], v[0]]); nrm = nrm if nrm @ u > 0 else -nrm
    orden = sorted(ids, key=lambda i: np.array(labs[i]["xy"]) @ nrm)
    resto = poly; res = {}
    for i in orden[:-1]:
        lo, hi = (xy @ nrm).min(), (xy @ nrm).max()
        for _ in range(60):
            t = (lo + hi) / 2
            half = Polygon([c + nrm * (t - (c @ nrm)) + v * 1e4, c + nrm * (t - (c @ nrm)) - v * 1e4,
                            c + nrm * (t - (c @ nrm) - 1e4) - v * 1e4, c + nrm * (t - (c @ nrm) - 1e4) + v * 1e4])
            a = resto.intersection(half).area
            lo, hi = (t, hi) if a < labs[i]["m2_dxf"] else (lo, t)
        pieza = resto.intersection(half); res[i] = pieza; resto = resto.difference(half)
    res[orden[-1]] = resto
    return res
for k, ids in con_rotulo.items():
    if len(ids) < 2: continue
    tot = sum(labs[i]["m2_dxf"] for i in ids)
    if not 0.95 < caras[k].area / tot < 1.05: continue
    for i, g in cortar(caras[k], ids).items():
        if g.geom_type != "Polygon": g = max(g.geoms, key=lambda q: q.area)
        geom[i] = g; metodo[i] = "ajustada"

faltan = [labs[i]["codigo"] for i in range(len(labs)) if i not in geom]
print("métodos", collections.Counter(metodo.values()), "sin contorno", faltan)

T = Transformer.from_crs(32619, 4326, always_xy=True).transform
feats, utm = [], []
for i, l in enumerate(labs):
    if i not in geom: continue   # (no ocurre con el DXF de 2026-11-04)
    g = geom[i].simplify(0.05)
    pr = {k: l[k] for k in ("codigo", "etiqueta_dxf", "etapa", "manzana", "lote", "m2_dxf", "uso_dxf")}
    pr["geometria"] = metodo[i]; pr["m2_geom"] = round(geom[i].area, 2)
    utm.append({"type": "Feature", "properties": pr, "geometry": mapping(g)})
    gw = transform(T, g)
    feats.append({"type": "Feature", "properties": pr, "geometry": {"type": "Polygon",
                  "coordinates": [[[round(x, 7), round(y, 7)] for x, y in gw.exterior.coords]]}})
json.dump({"type": "FeatureCollection", "features": feats}, open(f"{out}/lots.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"type": "FeatureCollection", "features": utm}, open(f"{base}/privado/lots_v3_utm.geojson", "w"))

M = collections.defaultdict(list)
for i, l in enumerate(labs):
    if i in geom: M[(l["etapa"], l["manzana"])].append(geom[i])
mf = []
for (e, m), gs in sorted(M.items()):
    u = unary_union([x.buffer(0.3, join_style=2) for x in gs]).buffer(-0.3, join_style=2)
    mf.append({"type": "Feature", "properties": {"etapa": e, "manzana": m}, "geometry": mapping(transform(T, u.simplify(0.1)))})
json.dump({"type": "FeatureCollection", "features": mf}, open(f"{out}/manzanas.json", "w"), separators=(",", ":"))

def anillo(p): return {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon",
                       "coordinates": [[[round(x, 7), round(y, 7)] for x, y in transform(T, p).exterior.coords]]}}
json.dump(anillo(perim.simplify(0.5)), open(f"{out}/limite.json", "w"))
json.dump(anillo(perim.buffer(12, join_style=1).simplify(1)), open(f"{out}/mascara.json", "w"))

am = []
for pr, xy in otros:
    m = re.match(r"^AV-PARQUE\s*(\d+)", pr[0])
    if not m: continue
    area = float(re.sub(r"[^\d.]", "", pr[-1].replace(",", "")) or 0)
    if area < 2000: continue
    lon, lat = T(*xy)
    am.append({"type": "Feature", "properties": {"nombre": "Área verde", "descripcion": f"Parque {int(m.group(1))} · {area:,.0f} m² (según plano)"},
               "geometry": {"type": "Point", "coordinates": [round(lon, 7), round(lat, 7)]}})
json.dump({"type": "FeatureCollection", "features": am}, open(f"{out}/amenidades.json", "w"), ensure_ascii=False, separators=(",", ":"))

c = np.array([l["xy"] for l in labs]).mean(0)
rep = {"rotulos": len(labs), "caras": len(caras), "metodos": dict(collections.Counter(metodo.values())), "sin_contorno": faltan,
       "ajustadas": [labs[i]["codigo"] for i in metodo if metodo[i] == "ajustada"],
       "perimetro_m2": round(perim.area), "amenidades": len(am), "centro_wgs84": T(*c)}
json.dump(rep, open(f"{base}/privado/reporte_extraccion_v3.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False))
