/*
 * CONFIGURACIÓN — Samanes del Este. Único archivo a tocar para ajustes comerciales.
 */
window.MASTERPLAN_CONFIG = {
  id: "sde",
  proyecto: {
  sigla: "SDE",
    nombre: "Samanes del Este",
    subtitulo: "",
    ubicacion: "",
    logo: null, logoClaro: null,               // sin logo todavía: wordmark de texto
    logoTexto: "Samanes del Este",
  },

  marca: {
    nombre: "PRAGMA CAPITAL",
    logo: "assets/logo-pragma-oscuro.png",
    logoClaro: "assets/logo-pragma.png",
    colores: { primario: "#205810", secundario: "#123408", acento: "#70D860" },  // misma paleta Pragma/PDE
    fuente: "Inter",
  },

  whatsapp: {
    numero: "18297623117",      // +1 (829) 762-3117 — ventas
    esEjemplo: false,
    mensaje: "Hola, me interesa el lote {codigo} de Samanes del Este",
  },

  // modo "geo": coordenadas reales [lng, lat] (WGS84) sobre imagen satelital.
  plano: {
    modo: "geo",
    teselas: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    atribucion: "Imágenes © Esri, Maxar, Earthstar Geographics",
    maxZoomNativo: 18,
    zoomEtiquetas: 18,
    zoomManzanas: 16,         // a partir de este zoom se ven los números de manzana          // a partir de este zoom se ven los códigos de lote
  },

  // Entorno fuera del límite. Para quitar el efecto: difuminado: false
  entorno: { difuminado: true, intensidad: 1 },   // intensidad 0–1 (1 = desenfoque 2.5px, −20% color, −13% brillo)
  // Zonas que se ocultan siempre con desenfoque fuerte, [[lat, lng], ...]. [] = ninguna
  zonasOcultas: [
    // galpones al sur de los lotes
    [[19.1964, -70.4914], [19.1964, -70.4876], [19.1898, -70.4876], [19.1898, -70.4914]],
    // galpones al este
    [[19.2018, -70.4868], [19.2018, -70.4822], [19.1966, -70.4822], [19.1966, -70.4868]]
  ],

  datos: {
    lotes: "proyectos/sde/data/lots.geojson",            // geometría (tools/extraer_dxf.py)
    inventario: "proyectos/sde/data/inventario.json",    // estado / m² / tipología (tools/merge_inventario.py) — SIN precios
    amenidades: "proyectos/sde/data/amenidades.json",
    manzanas: "proyectos/sde/data/manzanas.json",
    limite: "proyectos/sde/data/limite.json", mascara: "proyectos/sde/data/mascara.json",
    precios: "proyectos/sde/data/precios.json",          // solo se lee si mostrarPrecios = true (no existe en el sitio público)
    apiInventario: null,                   // futuro: endpoint de solo lectura de SIGI
  },

  // PRECIOS: apagado hasta que se apruebe la lista. Con true se muestra "RD$ X/m²" y un total
  // estimado (m² × precio, marcado "estimado"), leyendo datos.precios.
  mostrarPrecios: false,
  moneda: "RD$",

  estados: {
    disponible:    { etiqueta: "Disponible",    color: "#22E06B" },
    reservado:     { etiqueta: "Reservado",     color: "#FBBF24" },
    vendido:       { etiqueta: "Vendido",       color: "#35524D" },
    no_disponible: { etiqueta: "No disponible", color: "#C9D1CF" },
  },
  // Estado que se asigna a lotes del plano que no están en el inventario (se marcan "ej").
  estadoSinInventario: "no_disponible",
};
