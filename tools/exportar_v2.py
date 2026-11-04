import json
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union
T=Transformer.from_crs(32619,4326,always_xy=True).transform
d=json.load(open("privado/lots_v2_utm.geojson")); out=[]; G=[]
for f in d["features"]:
    g=shape(f["geometry"])
    if g.is_empty: g=shape(f["geometry"]).buffer(0)
    G.append(g); g2=transform(T,g)
    p=f["properties"]; p["geometria"]="aproximada"
    out.append({"type":"Feature","properties":p,"geometry":json.loads(json.dumps(mapping(g2)))})
json.dump({"type":"FeatureCollection","features":out},open("data/lots.geojson","w"),separators=(",",":"))
# manzanas y límite del proyecto
import collections
M=collections.defaultdict(list)
for f,g in zip(out,G):
    if not g.is_empty: M[(f["properties"]["etapa"],f["properties"]["manzana"])].append(g)
mf=[]
for (e,m),gs in M.items():
    u=unary_union([x.buffer(1.5,join_style=2) for x in gs]).buffer(-1.5,join_style=2)
    mf.append({"type":"Feature","properties":{"etapa":e,"manzana":m},"geometry":mapping(transform(T,u))})
json.dump({"type":"FeatureCollection","features":mf},open("data/manzanas.json","w"),separators=(",",":"))
lim=unary_union([g.buffer(25) for g in G if not g.is_empty]).buffer(-12).simplify(3)
json.dump({"type":"Feature","properties":{},"geometry":mapping(transform(T,lim))},open("data/limite.json","w"))
print(len(out),len(mf))
