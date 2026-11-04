"""Geometría v2: teselado regular por manzana + polígonos reales de DS_1 donde calzan.
Entrada: privado/lots_utm.geojson (etiquetas con codigo/etapa/manzana/m2_dxf; el centro = etiqueta)
         /workspace/paraiso/ds1.pkl (polilíneas de parcelas del bloque DS_1)
Salida:  privado/lots_v2_utm.geojson
Método por manzana (etapa+manzana, separada en grupos si hay etiquetas a >35 m):
 1. Eje de la manzana por PCA de las etiquetas -> coordenadas (a = a lo largo, b = transversal).
 2. Filas = grupos de b separados >6 m. Filas de 1–2 etiquetas se unen a la fila más cercana (lotes de cabecera).
 3. Cada fila es una franja: fondo compartido en el punto medio entre filas; borde exterior = fondo por área (m²/frente).
 4. Dentro de la franja, cortes perpendiculares al eje en el punto medio entre etiquetas consecutivas
    -> rectángulos contiguos, mismo ángulo, sin huecos ni solapes. Extremos alineados para toda la manzana.
 5. Si una fila no es recta (residuo > 3 m) se usa el mismo esquema con tangente local (manzanas curvas).
 6. Si la manzana tiene >=80 % de sus etiquetas dentro de una parcela DS_1 de área ±12 %, se usan esas parcelas reales.
"""
import json, pickle, math, collections, sys
import numpy as np
from shapely.geometry import Polygon, Point, LineString, mapping, shape
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
base = sys.argv[1] if len(sys.argv) > 1 else "."
d = json.load(open(f"{base}/privado/lots_utm.geojson"))
L = []
for f in d["features"]:
    p = dict(f["properties"]); c = shape(f["geometry"]).centroid
    L.append(p)
# etiqueta original (posición exacta) desde labels.pkl
lab = pickle.load(open("/workspace/paraiso/labels.pkl", "rb"))
pos = {}
for t, pt in lab:
    pr = t.split("\n"); _, m, l = pr[0].strip().split("-"); e = pr[3].split(":")[1].strip()
    pos[f"E{int(e)}-M{int(m)}-L{int(l)}"] = np.array([pt[0], pt[1]])
for p in L: p["xy"] = pos[p["codigo"]]

# --- DS_1
g = pickle.load(open("/workspace/paraiso/ds1.pkl", "rb"))
polys = list(polygonize(unary_union([LineString(q) for q in g["parcels"] if len(q) > 1])))
tree = STRtree(polys)
def ds1_de(p):
    pt = Point(*p["xy"]); hit = [polys[i] for i in tree.query(pt) if polys[i].contains(pt)]
    if not hit: return None
    h = min(hit, key=lambda q: q.area)
    return h if 0.88 < h.area / p["m2_dxf"] < 1.12 else None

def grupos(idx):
    # separa etiquetas de una manzana en componentes conectadas (vecinos < 35 m)
    idx = list(idx); out = []; rest = set(idx)
    while rest:
        s = [rest.pop()]; comp = []
        while s:
            i = s.pop(); comp.append(i)
            cerca = [j for j in rest if np.hypot(*(L[i]["xy"] - L[j]["xy"])) < 35]
            for j in cerca: rest.discard(j); s.append(j)
        out.append(comp)
    return out

def rect(c, u, v, a0, a1, b0, b1):
    return Polygon([c + u * a0 + v * b0, c + u * a1 + v * b0, c + u * a1 + v * b1, c + u * a0 + v * b1])

geom = {}; metodo = {}
man = collections.defaultdict(list)
for i, p in enumerate(L): man[(p["etapa"], p["manzana"])].append(i)
stats = collections.Counter()
for key, idx in man.items():
    reales = {i: ds1_de(L[i]) for i in idx}
    if sum(r is not None for r in reales.values()) >= 9.0 * len(idx):  # DS_1 desactivado: solo calza 313/1379 etiquetas
        usados = set()
        for i, r in reales.items():
            if r is not None and id(r) not in usados:
                geom[i] = r; metodo[i] = "real_ds1"; usados.add(id(r))
        idx = [i for i in idx if i not in geom]
        stats["real"] += len(usados)
    for comp in grupos(idx):
        P = np.array([L[i]["xy"] for i in comp]); c = P.mean(0)
        if len(comp) == 1:
            s = math.sqrt(L[comp[0]]["m2_dxf"]); u = np.array([1.0, 0]); v = np.array([0, 1.0])
            geom[comp[0]] = rect(c, u, v, -s / 2, s / 2, -s / 2, s / 2); metodo[comp[0]] = "aprox"; continue
        w, V = np.linalg.eigh(np.cov((P - c).T)); u = V[:, 1]; v = np.array([-u[1], u[0]])
        A = (P - c) @ u; B = (P - c) @ v
        # filas
        o = np.argsort(B); filas = [[o[0]]]
        for k in o[1:]:
            if B[k] - B[filas[-1][-1]] > 6: filas.append([k])
            else: filas[-1].append(k)
        grandes = [f for f in filas if len(f) > 2]
        if grandes and len(grandes) < len(filas):
            for f in [f for f in filas if len(f) <= 2]:
                bm = np.mean(B[f]); dest = min(grandes, key=lambda gg: abs(np.mean(B[gg]) - bm)); dest.extend(f)
            filas = grandes
        filas.sort(key=lambda f: np.mean(B[f]))
        bmed = [float(np.median(B[f])) for f in filas]
        curva = any(np.abs(B[f] - np.median(B[f])).max() > 3 for f in filas) and len(filas) == 1
        if curva:
            # cadena con tangente local: ordenar por A no sirve en curvas fuertes -> recorrer vecino más cercano
            f = filas[0]; pts = P[f]; orden = [int(np.argmin(A[f]))]; resto = set(range(len(f))) - set(orden)
            while resto:
                j = min(resto, key=lambda r: np.hypot(*(pts[r] - pts[orden[-1]]))); orden.append(j); resto.discard(j)
            pts = pts[orden]; ids = [comp[f[j]] for j in orden]
            fondo = np.median([L[i]["m2_dxf"] for i in ids]) / max(np.median(np.hypot(*np.diff(pts, axis=0).T)), 4)
            cortes = [pts[0] - (pts[1] - pts[0]) / 2] + [(pts[k] + pts[k + 1]) / 2 for k in range(len(pts) - 1)] + [pts[-1] + (pts[-1] - pts[-2]) / 2]
            def tang(k):
                a, b = pts[max(k - 1, 0)], pts[min(k, len(pts) - 1)]
                if k == 0 or k == len(pts): a, b = pts[0], pts[1] if k == 0 else pts[-1]
                if k == len(pts): a, b = pts[-2], pts[-1]
                t = b - a; t = t / (np.linalg.norm(t) or 1); return np.array([-t[1], t[0]])
            nrm = [tang(k) for k in range(len(cortes))]
            for k, i in enumerate(ids):
                n0, n1 = nrm[k], nrm[k + 1]; h = fondo / 2
                geom[i] = Polygon([cortes[k] - n0 * h, cortes[k + 1] - n1 * h, cortes[k + 1] + n1 * h, cortes[k] + n0 * h]); metodo[i] = "aprox"
            stats["curva"] += len(ids); continue
        # extremos comunes de la manzana
        pasos = []
        for f in filas:
            s = np.sort(A[f]); pasos += list(np.diff(s))
        paso = float(np.median([x for x in pasos if x > 2])) if pasos else 10.0
        amin, amax = A.min() - paso / 2, A.max() + paso / 2
        for r, f in enumerate(filas):
            f = sorted(f, key=lambda k: A[k]); a = A[f]
            fondo = float(np.median([L[comp[k]]["m2_dxf"] for k in f]) / max(paso, 4))
            b0 = (bmed[r - 1] + bmed[r]) / 2 if r > 0 else bmed[r] - fondo / 2
            b1 = (bmed[r] + bmed[r + 1]) / 2 if r < len(filas) - 1 else bmed[r] + fondo / 2
            if r == 0 and len(filas) > 1: b0 = b1 - max(fondo, 2 * (b1 - bmed[r]))
            if r == len(filas) - 1 and len(filas) > 1: b1 = b0 + max(fondo, 2 * (bmed[r] - b0))
            ext0 = min(amin, a[0] - paso / 2) if len(f) > 1 else a[0] - paso / 2
            ext1 = max(amax, a[-1] + paso / 2) if len(f) > 1 else a[0] + paso / 2
            # filas mucho más cortas que la manzana no se estiran
            if a[0] - amin > 1.5 * paso: ext0 = a[0] - paso / 2
            if amax - a[-1] > 1.5 * paso: ext1 = a[-1] + paso / 2
            cuts = [ext0] + [(a[k] + a[k + 1]) / 2 for k in range(len(a) - 1)] + [ext1]
            for k, kk in enumerate(f):
                geom[comp[kk]] = rect(c, u, v, cuts[k], cuts[k + 1], b0, b1); metodo[comp[kk]] = "aprox"
        stats["teselado"] += len(comp)

# quitar solapes con parcelas reales y entre manzanas (las reales mandan)
reales = [geom[i] for i in geom if metodo[i] == "real_ds1"]
U = unary_union(reales) if reales else None
for i in list(geom):
    gg = geom[i]
    if metodo[i] != "real_ds1" and U is not None and gg.intersects(U):
        gg = gg.difference(U)
    gg = gg.buffer(0)
    if gg.geom_type != "Polygon": gg = max(gg.geoms, key=lambda q: q.area)
    geom[i] = gg.simplify(0.2)
feats = []
for i, p in enumerate(L):
    pr = {k: v for k, v in p.items() if k != "xy"}; pr["geometria"] = "real" if metodo[i] == "real_ds1" else "aproximada"
    pr["m2_geom_aprox"] = round(geom[i].area, 1)
    feats.append({"type": "Feature", "properties": pr, "geometry": mapping(geom[i])})
json.dump({"type": "FeatureCollection", "features": feats}, open(f"{base}/privado/lots_v2_utm.geojson", "w"))
print(stats, collections.Counter(metodo.values()))
