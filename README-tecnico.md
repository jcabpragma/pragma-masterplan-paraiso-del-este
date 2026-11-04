# Masterplan interactivo — Paraíso del Este (README técnico)

Sitio estático (HTML + Leaflet + GeoJSON), sin build. Se publica tal cual en Render (Static Site).

```
index.html            entrada + plano
config.js             ÚNICO archivo de ajustes comerciales (WhatsApp, colores, estados, mostrarPrecios)
js/app.js             lógica (mapa, filtros por estado y etapa, tarjeta, ficha)
css/styles.css        estilos (marca Pragma: #0B3B33 / #003527, Inter)
data/lots.geojson     geometría de los 1.379 lotes (WGS84) — generada por tools/extraer_dxf.py
data/inventario.json  estado / m² / tipología por código — generado por tools/merge_inventario.py (SIN precios)
data/amenidades.json  pines de amenidades (vacío: ver "Amenidades")
tools/                scripts de extracción, merge y pruebas
privado/              (NO se sube: .gitignore) precios, geometría UTM, reportes
```

## 1. De dónde sale el plano (DXF)

Archivo recibido: `plano.dxf` (147 MB, AutoCAD Civil 3D). Coordenadas **UTM zona 19N, EPSG:32619, metros**
(`$INSUNITS = 6`); el proyecto queda en ~18.548 N, −69.809 O (Santo Domingo Este) y calza con la imagen satelital.

**El DXF llegó truncado**: termina en medio de una entidad de `ENTITIES` (sin `ENDSEC`/`OBJECTS`/`EOF`).
`tools/extraer_dxf.py` crea una copia reparada (corta en la última entidad completa y cierra el archivo) y la lee
con `ezdxf.recover`.

Capas usadas:

| Capa | Uso |
|---|---|
| `NOMBRES` (MTEXT) | Etiqueta de cada parcela: `01-05-3 / 224.15 / Habitacional / Etapa: 1` → código, m², uso, etapa. **1.379 lotes.** |
| `DS_1` (bloque, Parcels Lines / textos) | Revisada: es otro trazado (zona norte/oeste) que no coincide con las etiquetas; no se usa para geometría. Sus rótulos (calles, «Paisaje», torres eléctricas) tampoco se usan como pines porque no están alineados con los lotes. |

> **Reemplazado en v7** (ver al final): el DXF completo del 2026-11-04 trae los linderos reales.

Las capas de polígonos de lote (`C-PROP-LOTS`, `Parcels Lines` del trazado actual) **no están en la parte legible del archivo**
(se perdieron con el truncado). Por eso la geometría es **aproximada**: un rectángulo por lote centrado en la etiqueta
(Civil 3D la ubica en el centroide), orientado según la fila de lotes de la misma manzana, ancho = separación entre
etiquetas vecinas y fondo = m² / ancho, recortado con Voronoi para que no se solapen. La ficha lo indica
(«Contorno del lote referencial»). Cuando llegue el DXF completo (o un DXF solo con las capas de lotes), sustituir el
paso 3 de `extraer_dxf.py` por los polígonos reales y volver a correr los dos scripts; el resto del sitio no cambia.

### Código de lote
Etiqueta DXF `01-MM-LL` + `Etapa: N`  →  **`E{N}-M{MM}-L{LL}`** sin ceros a la izquierda (formato SIGI), p. ej.
`01-05-48` Etapa 1 → `E1-M5-L48`. La manzana 11 existe en las etapas 2, 3 y 4, por eso la etapa es parte del código.

```bash
pip install ezdxf shapely pyproj
python3 tools/extraer_dxf.py /ruta/plano.dxf        # -> data/lots.geojson, privado/lots_utm.geojson
```

## 2. Inventario (SIGI) — cómo actualizarlo

CSV: `lote,manzana,m2,precio,estado,etiquetas` (lote = `E1-M1-L3`).

```bash
python3 tools/merge_inventario.py /ruta/inventario_pde.csv
git add data/inventario.json && git commit -m "Inventario AAAA-MM-DD" && git push   # Render redeploya solo
```

- Estados: `disponible` (verde), `reservado` (ámbar), `vendido` (gris), `no_disponible` (gris oscuro). `bloqueado` → `no_disponible`.
- m²: se usa el de SIGI. Tipología (`etiquetas`: habitacional / esquina) se muestra como etiqueta.
- Lotes del plano sin fila en SIGI: se muestran «No disponible» con marca **ej** y m² del DXF.
- `data/inventario.json` **no contiene precios**. Los precios van a `privado/precios.json` (ignorado por git).
- Reporte de coincidencias: `privado/reporte_merge.json`.

Futuro: `proyectos/pde/config.js → datos.apiInventario` puede apuntar a un endpoint de solo lectura que devuelva el mismo formato
(`{lotes: {codigo: {estado, m2, tipologia}}}` o lista con `codigo`); tiene prioridad sobre el JSON.

## 3. Precios (apagados)

`proyectos/pde/config.js → mostrarPrecios: false`. Mientras esté en `false` la tarjeta dice «Precio: Consultar por WhatsApp» y el sitio
no lee ningún precio. Para activarlos cuando se apruebe la lista:
1. `mostrarPrecios: true`;
2. copiar `privado/precios.json` a `data/precios.json` (formato `{lotes: {codigo: {precio_m2, moneda}}}`) y quitar
   `data/precios.json` del `.gitignore`.
La tarjeta mostrará `RD$ X/m²` y «Total estimado» (m² × precio, marcado *estimado*).

## 4. WhatsApp
`proyectos/pde/config.js → whatsapp.numero = "18297623117"` (+1 829 762-3117). Mensaje: «Hola, me interesa el lote {codigo} del proyecto Paraíso del Este».

## 5. Amenidades
Solo se ponen pines rotulados en el DXF. Los únicos rótulos encontrados (Paisaje, torres eléctricas, calles) están en el
trazado `DS_1`, que no coincide con los lotes, así que `data/amenidades.json` queda vacío hasta tener el plano completo.
Formato: `Point [lng, lat]` con `nombre`, `descripcion`.

## 6. Pruebas
```bash
python3 -m http.server 8765 &
python3 tools/prueba_capturas.py http://localhost:8765/ screenshots/local E1-M5-L48
```
Móvil 390×844 (entrada, plano completo, tap real en un lote, ficha, filtro etapa+estado) y escritorio 1280×800; verifica
que el link de WhatsApp lleve el código del lote y que no aparezca «RD$» en la página.

## 7. Publicación
Render Static Site conectado a este repo (rama `main`, publish path `.`, build `echo ok`). Cada push redeploya.

## v2 (nov 2026): geometría regular y nueva imagen
- **Geometría** (`tools/geometria_v2.py` → `tools/exportar_v2.py`): teselado regular por manzana a partir de las etiquetas del DXF
  (eje por PCA, filas, franjas con fondo compartido, cortes perpendiculares en el punto medio entre etiquetas; tangente local en manzanas curvas).
  Sin huecos ni solapes dentro de la manzana. Sigue siendo **aproximada**: las capas reales de lotes no están en el DXF (archivo truncado).
  Se probó usar DS_1: solo 313 de 1379 etiquetas caen en una parcela de área ±10 % (es otro diseño), así que se descartó.
  También genera `data/manzanas.json` (contornos) y `data/limite.json` (límite del proyecto).
- **Marca**: logos en `assets/` (versión a color, `-oscuro` para fondos oscuros, `-blanco`). Paleta verde tomada del logo Paraíso del Este.
- Flujo de actualización de geometría: `python3 tools/geometria_v2.py . && python3 tools/exportar_v2.py`.

## v4: varios proyectos
- `proyectos/proyectos.js`: lista de proyectos y selección por URL (`?p=pde`, `?p=sde`; `&ver=plano` salta la portada).
- `proyectos/<id>/config.js` (+ `data/` y logos del proyecto). Compartido: `assets/` (foto de portada, logos Pragma), `js/`, `css/`.
- SDE (Samanes del Este): `proyectos/sde/data/` se generó del DXF de Samanes (293 rótulos `M##-L` en capa 0 + 313 polilíneas cerradas
  en capa 0 = contornos reales: 292/293 coinciden en área ±5 %; M16-L10 queda aproximado). UTM 19N → WGS84.
  Sin inventario aún: todos «No disponible · ej». Al llegar el CSV se genera `proyectos/sde/data/inventario.json` igual que PDE.

## v7 (4 nov 2026): PDE con contornos reales
- Entrada: DXF completo de Paraíso del Este (29,8 MB, termina en `EOF`, AutoCAD 2013, todo en capa `0`, metros, UTM 19N).
- Script: `python3 tools/extraer_dxf_v3.py /ruta/plano_pde.dxf && python3 tools/merge_inventario.py /ruta/inventario_pde.csv pde`.
  Reemplaza a `extraer_dxf.py` + `geometria_v2.py` + `exportar_v2.py` para PDE (se dejan como historial).
- Método (igual que SDE, rótulo dentro de polígono): `polygonize` de LINE + LWPOLYLINE + ARC → 2.922 caras; cada uno de los
  1.379 rótulos MTEXT toma la cara más pequeña que lo contiene, aceptada si el área = m² del rótulo ±5 %.
  - **1.374** caras directas (área = m² con mediana 1,0000) + **1** cara partida por una línea ajena (E1-M3-L2, se une con su pedazo) → **1.375 reales**.
  - **4 ajustadas**: E1-M1-L12/L13 y E1-M1-L14/L15 comparten cara (falta el lindero entre ellos en el DXF); se cortan paralelo
    al lindero vecino en la posición que da el m² de cada rótulo. `geometria: "ajustada"` → la ficha muestra «Contorno referencial».
  - 0 lotes sin contorno. Sin solapes, todos válidos. Mismo sitio que la capa anterior (desplazamiento mediano 0,15 m).
- La ficha ya **no** muestra «Contorno del lote referencial» cuando `geometria === "real"` (aplica también a SDE: 292 reales, M16-L10 sigue con nota).
- Límite: LWPOLYLINE cerrada de 51,4 ha del DXF (contiene los 1.379 rótulos) → `limite.json`; `mascara.json` = límite + 12 m
  (recorte de la capa nítida; el entorno sigue con el difuminado claro).
- Manzanas: unión de los lotes reales por etapa+manzana (66).
- Amenidades: rótulos `AV-PARQUE nn` del DXF con ≥ 2.000 m² → 8 pines «Área verde». Se ven desde zoom 17
  (`plano.zoomAmenidades`) para no tapar la vista general. AI-1/AI-3 y AA- no se usan (no está claro qué son). Calles: no se dibujan.
- Inventario: 1.368 de 1.379 coinciden (sin cambio: los rótulos del DXF nuevo son los mismos). Siguen 11 solo en plano
  («No disponible · ej») y 12 solo en SIGI; ver `privado/reporte_merge.json`.

## v8 (4 nov 2026): selector Satélite | Mapa
- Botón segmentado «Satélite | Mapa» sobre el plano (móvil: arriba a la derecha; escritorio ≥900px: arriba a la izquierda, porque ahí la tarjeta del lote flota a la derecha). Usa `--primario`, así SDE sale en azul.
- Satélite = `CFG.plano.teselas` (Esri World Imagery, `maxZoomNativo` por proyecto). Mapa = OpenStreetMap estándar `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, nativo hasta z19 y ampliado hasta z21 (sin teselas en blanco). Atribución «© colaboradores de OpenStreetMap». CARTO Voyager se descartó: ahora exige API key (marca de agua «API KEY REQUIRED»).
- Para cambiar el mapa de calles por proyecto: `plano.mapaCalles: { url, atribucion, maxNativo, subdominios }` en `config.js`.
- La elección se guarda en `localStorage["pragma-masterplan-fondo"]` (`satelite` | `mapa`); por defecto Satélite.
- `ponerFondo()` (js/app.js) recrea las 3 capas de teselas (fondo, `nitido` recortado al límite, `ocultoRecorte` dentro de `oculto` para las zonas ocultas de SDE). Los recortes están en los panes, así no se duplican al cambiar.
- Entorno en modo Mapa: desenfoque leve (0.6px) y menos color, para no ensuciar las calles. Límite y contornos de manzana pasan a color `secundario` (el blanco no se ve sobre el mapa claro).
- Prueba: `python3 tools/captura_v8_fondo.py URL screenshots/live-v8` (PDE y SDE, 390x844 y 1280x800: por defecto, cambio, zoom máximo, tarjeta, recordar tras recargar, choques con filtros/zoom/leyenda/tarjeta, errores JS y teselas con error).
