"""Extrae los lotes de 'Paraíso del Este' desde el DXF y genera la geometría del masterplan.

Uso:  python3 tools/extraer_dxf.py /ruta/plano.dxf
Salida: data/lots.geojson (WGS84), privado/lots_utm.geojson (UTM 19N), privado/reporte_extraccion.json

Qué hace:
 1. Si el DXF está truncado (sin ENDSEC/EOF al final), crea una copia reparada cortando en la última
    entidad completa y cerrando la sección ENTITIES (el archivo recibido el 2026-11-03 venía truncado).
 2. Lee con ezdxf.recover y toma las etiquetas de parcela de la capa NOMBRES (MTEXT de Civil 3D):
       "01-05-3\\n224.15\\nHabitacional\\nEtapa: 1"  ->  proyecto-manzana-lote / m² / uso / etapa
    El código se normaliza al formato de SIGI: E{etapa}-M{manzana}-L{lote}  (p. ej. E1-M5-L3).
 3. Los polígonos de lote (capas C-PROP-LOTS / Parcels Lines) NO están en la parte legible del archivo,
    así que la geometría se APROXIMA: un rectángulo por lote centrado en la etiqueta (Civil 3D la pone en
    el centroide), orientado según la fila de lotes vecinos de la misma manzana, con ancho = separación entre
    etiquetas vecinas y fondo = m² / ancho, recortado con el diagrama de Voronoi para que no se solapen.
    Cuando llegue un DXF completo, reemplazar el paso 3 por los polígonos reales (ver README-tecnico.md).
Coordenadas: UTM zona 19N (EPSG:32619), unidades metros ($INSUNITS=6).
"""
import sys, os, re, json, math
import numpy as np
from ezdxf import recover
from shapely.geometry import Point, Polygon, MultiPoint, mapping
from shapely.ops import voronoi_diagram, transform  # noqa
from shapely.strtree import STRtree
from pyproj import Transformer

src = sys.argv[1] if len(sys.argv) > 1 else "/workspace/paraiso/plano.dxf"
base = os.path.dirname(os.path.abspath(__file__)) + "/.."
os.makedirs(f"{base}/privado", exist_ok=True)

# ---- 1. reparar si está truncado
data = open(src, "rb").read()
tail = data[-200:].replace(b"\r", b"")
reparado = src
if not tail.rstrip().endswith(b"EOF"):
    k = data.rfind(b"\r\n  0\r\n", 0, len(data) - 10)
    reparado = src.replace(".dxf", "_reparado.dxf")
    open(reparado, "wb").write(data[:k] + b"\r\n  0\r\nENDSEC\r\n  0\r\nEOF\r\n")
    print("DXF truncado: copia reparada en", reparado)
del data

# ---- 2. etiquetas
doc, auditor = recover.readfile(reparado)
msp = doc.modelspace()
lotes = []
for e in msp.query('MTEXT[layer=="NOMBRES"]'):
    partes = [p.strip() for p in e.plain_text().split("\n")]
    m = re.match(r"^(\d+)-(\d+)-(\d+)$", partes[0]) if partes else None
    if not m or len(partes) < 4:
        print("Etiqueta no reconocida:", partes); continue
    etapa = int(re.sub(r"\D", "", partes[3]))
    x, y = e.dxf.insert[0], e.dxf.insert[1]
    lotes.append(dict(codigo=f"E{etapa}-M{int(m.group(2))}-L{int(m.group(3))}", etiqueta_dxf=partes[0],
                      etapa=f"E{etapa}", manzana=int(m.group(2)), lote=int(m.group(3)),
                      m2_dxf=float(partes[1].replace(",", "")), uso_dxf=partes[2], x=x, y=y))
print("Etiquetas de lote:", len(lotes))

# ---- 3. geometría aproximada
P = np.array([[l["x"], l["y"]] for l in lotes])
vor = voronoi_diagram(MultiPoint([Point(*p) for p in P]), envelope=MultiPoint(P).envelope.buffer(200))
celdas = list(vor.geoms); tree = STRtree(celdas)
grupo = {}
for i, l in enumerate(lotes): grupo.setdefault((l["etapa"], l["manzana"]), []).append(i)
for i, l in enumerate(lotes):
    idx = [j for j in grupo[(l["etapa"], l["manzana"])] if j != i]
    if not idx: idx = [j for j in range(len(lotes)) if j != i]
    d = np.hypot(*(P[idx] - P[i]).T); orden = np.argsort(d); nn = d[orden[0]]
    # eje local de la fila: PCA de las 8 etiquetas más cercanas de la misma manzana
    loc = P[[i] + [idx[j] for j in orden[:8]]]
    if len(loc) >= 3:
        w, V = np.linalg.eigh(np.cov((loc - loc.mean(0)).T)); dirv = V[:, 1]
    else:
        dirv = (P[idx[orden[0]]] - P[i]) / nn
    dv = P[idx] - P[i]; a = dv @ dirv; p = dv @ np.array([-dirv[1], dirv[0]])
    misma_fila = (np.abs(p) < 4) & (np.abs(a) > 2)
    paso = float(np.abs(a[misma_fila]).min()) if misma_fila.any() else nn
    ancho = float(np.clip(paso, 6, 30)); fondo = float(np.clip(l["m2_dxf"] / ancho, 6, 60))
    if paso > 30: ancho = fondo = math.sqrt(l["m2_dxf"])
    u, n = dirv * ancho / 2, np.array([-dirv[1], dirv[0]]) * fondo / 2
    c = P[i]
    rect = Polygon([c - u - n, c + u - n, c + u + n, c - u + n])
    celda = [celdas[k] for k in tree.query(Point(*c)) if celdas[k].contains(Point(*c))][0]
    g = rect.intersection(celda).buffer(-0.3, join_style=2)
    if g.geom_type != "Polygon": g = max(g.geoms, key=lambda q: q.area)
    l["geom_utm"] = g; l["m2_geom_aprox"] = round(g.area, 1)

# ---- salida
tr = Transformer.from_crs(32619, 4326, always_xy=True)
def fc(geo):
    feats = []
    for l in lotes:
        g = l["geom_utm"] if not geo else transform(lambda x, y, z=None: tr.transform(x, y), l["geom_utm"])
        coords = [[round(a, 7 if geo else 3), round(b, 7 if geo else 3)] for a, b in g.exterior.coords]
        props = {k: l[k] for k in ("codigo", "etiqueta_dxf", "etapa", "manzana", "lote", "m2_dxf", "uso_dxf", "m2_geom_aprox")}
        props["geometria"] = "aproximada"
        feats.append({"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [coords]}})
    return {"type": "FeatureCollection", "metadata": {"proyecto": "Paraíso del Este",
            "fuente": "DXF capa NOMBRES (etiquetas Civil 3D)", "crs": "EPSG:4326" if geo else "EPSG:32619",
            "nota": "Geometría aproximada a partir de etiquetas; el DXF recibido está truncado y no trae los polígonos de lote."},
            "features": feats}
json.dump(fc(True), open(f"{base}/data/lots.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(fc(False), open(f"{base}/privado/lots_utm.geojson", "w"), ensure_ascii=False)
json.dump({"etiquetas": len(lotes), "insunits": doc.header.get("$INSUNITS"), "crs": "EPSG:32619",
           "centro_wgs84": tr.transform(*P.mean(0))}, open(f"{base}/privado/reporte_extraccion.json", "w"), indent=1)
print("OK", len(lotes), "lotes; centro WGS84", tr.transform(*P.mean(0)))
