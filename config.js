/*
 * CONFIGURACIÓN — Paraíso del Este. Único archivo a tocar para ajustes comerciales.
 */
window.MASTERPLAN_CONFIG = {
  proyecto: {
    nombre: "Paraíso del Este",
    subtitulo: "Masterplan interactivo · Santo Domingo Este",
    ubicacion: "Santo Domingo Este, República Dominicana",
    logo: "assets/logo-paraiso-oscuro.png",      // versión para fondo oscuro (intro)
    logoClaro: "assets/logo-paraiso.png",       // versión a color (encabezado claro)
    fondoIntro: "assets/intro.jpg",
    logoTexto: "Paraíso del Este",
  },

  marca: {
    nombre: "PRAGMA CAPITAL",
    logo: "assets/logo-pragma-oscuro.png",
    logoClaro: "assets/logo-pragma.png",
    colores: { primario: "#205810", secundario: "#123408", acento: "#70D860" },  // verdes del logo Paraíso del Este,
    fuente: "Inter",
  },

  whatsapp: {
    numero: "18297623117",      // +1 (829) 762-3117 — ventas
    esEjemplo: false,
    mensaje: "Hola, me interesa el lote {codigo} del proyecto {proyecto}",
  },

  // modo "geo": coordenadas reales [lng, lat] (WGS84) sobre imagen satelital.
  plano: {
    modo: "geo",
    teselas: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    atribucion: "Imágenes © Esri, Maxar, Earthstar Geographics",
    maxZoomNativo: 19,
    zoomEtiquetas: 18.5,
    zoomManzanas: 16.5,         // a partir de este zoom se ven los números de manzana          // a partir de este zoom se ven los códigos de lote
  },

  datos: {
    lotes: "data/lots.geojson",            // geometría (tools/extraer_dxf.py)
    inventario: "data/inventario.json",    // estado / m² / tipología (tools/merge_inventario.py) — SIN precios
    amenidades: "data/amenidades.json",
    manzanas: "data/manzanas.json",
    limite: "data/limite.json",
    precios: "data/precios.json",          // solo se lee si mostrarPrecios = true (no existe en el sitio público)
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
