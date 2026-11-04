/* Masterplan interactivo — Paraíso del Este. Sin build: Leaflet + config.js + GeoJSON + inventario.json */
(function () {
  "use strict";
  var CFG = window.MASTERPLAN_CONFIG;
  var $ = function (s) { return document.querySelector(s); };
  var estadoActivo = "todos", etapaActiva = "todas";
  var lotes = [], capas = {}, seleccionado = null, map, precios = {};

  // ---------- Marca / tema ----------
  var root = document.documentElement.style;
  root.setProperty("--primario", CFG.marca.colores.primario);
  root.setProperty("--secundario", CFG.marca.colores.secundario);
  root.setProperty("--acento", CFG.marca.colores.acento);
  Object.keys(CFG.estados).forEach(function (k) { root.setProperty("--" + k, CFG.estados[k].color); });
  document.title = "Masterplan · " + CFG.proyecto.nombre;

  function esc(t) { return String(t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  // "ej" por lote: solo en lotes del plano que no tienen inventario de SIGI
  function ejTag(p) { return p && p.ejemplo ? '<span class="ej" title="Sin inventario confirmado">ej</span>' : ""; }
  function wordmark() {
    if (CFG.marca.logo) return '<img src="' + esc(CFG.marca.logo) + '" alt="' + esc(CFG.marca.nombre) + '">';
    return '<span class="lam">Λ</span>' + esc(CFG.marca.nombre);
  }
  function num(v, d) { return Number(v).toLocaleString("en-US", { maximumFractionDigits: d == null ? 2 : d }); }
  function dinero(v) { return CFG.moneda + " " + num(v, 0); }

  // ---------- WhatsApp ----------
  function linkWhatsApp(codigo) {
    var msg = CFG.whatsapp.mensaje.replace("{codigo}", codigo).replace("{proyecto}", CFG.proyecto.nombre);
    return "https://wa.me/" + CFG.whatsapp.numero.replace(/\D/g, "") + "?text=" + encodeURIComponent(msg);
  }
  var icoWA = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.4.1-.2 0-.3 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3z"/></svg>';

  // ---------- Intro ----------
  $("#introLogo").innerHTML = CFG.proyecto.logo
    ? '<img src="' + esc(CFG.proyecto.logo) + '" alt="' + esc(CFG.proyecto.nombre) + '">'
    : '<span class="intro__nombre">' + esc(CFG.proyecto.logoTexto) + "</span>";
  $("#tituloProyecto").textContent = CFG.proyecto.nombre;
  $("#marcaMini").src = CFG.marca.logoClaro || CFG.marca.logo; $("#marcaMini").alt = CFG.marca.nombre;
  if (CFG.proyecto.logoClaro || CFG.proyecto.logo) { $("#logoTop").src = CFG.proyecto.logoClaro || CFG.proyecto.logo; $("#logoTop").alt = CFG.proyecto.nombre; }
  else { $("#logoTop").hidden = true; $("#tituloProyecto").classList.remove("sr-only"); }

  // ---------- Selector de proyecto (?p=pde / ?p=sde) ----------
  var PROY = window.MASTERPLAN_PROYECTOS || [];
  var qs = new URLSearchParams(location.search);
  document.querySelectorAll(".proy-tabs").forEach(function (nav) {
    nav.innerHTML = PROY.map(function (x) {
      var act = x.id === CFG.id;
      var dentro = nav.classList.contains("proy-tabs--intro") ? "" : "&ver=plano";
      return '<a class="proy-tab" href="?p=' + x.id + dentro + '"' + (act ? ' aria-current="page"' : "") + '><b>' + esc(x.sigla) + '</b><span> · ' + esc(x.nombre) + "</span></a>";
    }).join("");
  });
  function entrar() {
    $("#intro").hidden = true; $("#app").hidden = false;
    if (CFG.proximamente) return mostrarProximamente();
    if (!map) iniciarMapa(); else map.invalidateSize();
  }
  function mostrarProximamente() {
    ["#filtros", "#filtrosEtapa", "#map", "#leyenda"].forEach(function (s) { $(s).hidden = true; });
    $("#proximamente").hidden = false;
    $("#proximamente").innerHTML = '<div class="proximo__box"><span class="proximo__pill">Próximamente</span><h1>' + esc(CFG.proyecto.nombre) + "</h1><p>" + esc(CFG.proyecto.nota || "Masterplan en preparación") + "</p>" +
      '<a id="btnWA" class="btn btn--wa btn--lg" href="https://wa.me/' + CFG.whatsapp.numero + "?text=" + encodeURIComponent(CFG.whatsapp.mensaje) + '" target="_blank" rel="noopener">' + icoWA + "Escribir por WhatsApp</a></div>";
    document.body.setAttribute("data-listo", "1");
  }
  $("#btnIngresar").addEventListener("click", entrar);
  if (qs.get("ver") === "plano") entrar();
  $("#btnVolver").addEventListener("click", function () { cerrarCard(); $("#app").hidden = true; $("#intro").hidden = false; });

  function aLatLng(c) { return [c[1], c[0]]; }
  function getJSON(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + " " + r.status); return r.json(); }); }

  // ---------- Mapa ----------
  function iniciarMapa() {
    map = L.map("map", { zoomControl: true, zoomSnap: 0.25, maxZoom: 21 });
    var opTes = { maxZoom: 21, maxNativeZoom: CFG.plano.maxZoomNativo || 19, attribution: CFG.plano.atribucion };
    var conMascara = !!CFG.datos.mascara;   // fondo: con máscara se pide a baja resolución (z<=15) para que nada se reconozca al acercar
    L.tileLayer(CFG.plano.teselas, conMascara ? L.extend({}, opTes, { maxNativeZoom: 14 }) : opTes).addTo(map);   // fondo (difuminado si hay máscara)
    map.createPane("nitido"); map.getPane("nitido").style.zIndex = 210; map.getPane("nitido").style.pointerEvents = "none";
    map.createPane("vineta"); map.getPane("vineta").style.zIndex = 300; map.getPane("vineta").style.pointerEvents = "none";
    map.zoomControl.setPosition("bottomright");
    map.on("click", cerrarCard);
    map.createPane("manzanas"); map.getPane("manzanas").style.zIndex = 450; map.getPane("manzanas").style.pointerEvents = "none";
    function etiquetas() {
      var z = map.getZoom(), c = map.getContainer();
      c.classList.toggle("sin-etiquetas", z < (CFG.plano.zoomEtiquetas || 18));
      c.classList.toggle("sin-manzanas", z < (CFG.plano.zoomManzanas || 16.5) || z >= (CFG.plano.zoomEtiquetas || 18));
    }
    map.on("zoomend", etiquetas); etiquetas();

    Promise.all([
      getJSON(CFG.datos.lotes),
      getJSON(CFG.datos.amenidades).catch(function () { return { features: [] }; }),
      getJSON(CFG.datos.inventario).catch(function () { return null; }),
      cargarInventarioVivo(),
      CFG.mostrarPrecios ? getJSON(CFG.datos.precios).catch(function () { return null; }) : Promise.resolve(null),
      CFG.datos.manzanas ? getJSON(CFG.datos.manzanas).catch(function () { return null; }) : Promise.resolve(null),
      CFG.datos.limite ? getJSON(CFG.datos.limite).catch(function () { return null; }) : Promise.resolve(null),
      CFG.datos.mascara ? getJSON(CFG.datos.mascara).catch(function () { return null; }) : Promise.resolve(null)
    ]).then(function (res) {
      lotes = res[0].features;
      precios = (res[4] && res[4].lotes) || {};
      mezclarInventario(res[3] || res[2]);
      encuadrar();
      if (res[7]) aplicarMascara(res[7], opTes);      // antes de dibujar: Leaflet crea los <path> solo cuando el mapa ya tiene vista
      if (res[6]) L.geoJSON(res[6], { interactive: false, style: { color: "#FFFFFF", weight: 2, opacity: 0.85, dashArray: "6 6", fill: false } }).addTo(map);
      if (res[5]) dibujarManzanas(res[5].features);
      dibujarLotes();
      dibujarAmenidades(res[1].features);
      dibujarFiltros(); dibujarLeyenda();
      document.body.setAttribute("data-listo", "1");
    }).catch(function (e) {
      console.error(e);
      alert("No se pudieron cargar los datos del plano. Abra el sitio con un servidor (ver README).");
    });
  }
  // Fuera del proyecto: fondo difuminado + capa nítida recortada al límite + viñeta oscura con borde suave
  function aplicarMascara(gj, opTes) {
    var anillo = gj.geometry.coordinates[0].map(aLatLng);
    L.tileLayer(CFG.plano.teselas, L.extend({ pane: "nitido", attribution: "" }, opTes)).addTo(map);
    var pane = map.getPane("nitido");
    function camino(fn) { return "path('M" + anillo.map(function (ll) { var p = fn(ll); return p.x.toFixed(1) + " " + p.y.toFixed(1); }).join("L") + "Z')"; }
    function actualizar() { pane.style.transition = "none"; pane.style.clipPath = pane.style.webkitClipPath = camino(function (ll) { return map.latLngToLayerPoint(ll); }); }
    map.on("move zoom viewreset zoomend moveend resize", actualizar);
    map.on("zoomanim", function (e) {   // sigue la animación de zoom de Leaflet (misma curva y duración)
      var c = camino(function (ll) { return map._latLngToNewLayerPoint(ll, e.zoom, e.center); });
      pane.style.transition = "clip-path .25s cubic-bezier(0,0,.25,1), -webkit-clip-path .25s cubic-bezier(0,0,.25,1)";
      pane.style.clipPath = pane.style.webkitClipPath = c;
    });
    actualizar();
    var mundo = [[-89, -179.9], [-89, 179.9], [89, 179.9], [89, -179.9]];
    L.polygon([mundo, anillo], { renderer: L.svg({ pane: "vineta", padding: 1 }), interactive: false, stroke: true, color: "#000", weight: 26, opacity: 0.35, fillColor: "#000", fillOpacity: 0.42 }).addTo(map);
    map.getContainer().classList.add("con-mascara");
  }
  // Vista inicial: todo el proyecto, también en celular
  function encuadrar() {
    var b = L.latLngBounds([]);
    lotes.forEach(function (f) { f.geometry.coordinates[0].forEach(function (c) { b.extend(aLatLng(c)); }); });
    if (b.isValid()) { map.fitBounds(b, { padding: window.innerWidth < 600 ? [6, 6] : [24, 24] }); map.setMaxBounds(b.pad(1.5)); map.setMinZoom(Math.max(map.getZoom() - 2, 3)); }
  }

  function cargarInventarioVivo() {
    if (!CFG.datos.apiInventario) return Promise.resolve(null);
    return fetch(CFG.datos.apiInventario, { headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }
  // inventario: { lotes: { "E1-M1-L3": { estado, m2, tipologia:[...] } } }  (también acepta lista con "codigo")
  function mezclarInventario(inv) {
    var porCodigo = {};
    if (inv && inv.lotes) {
      if (Array.isArray(inv.lotes)) inv.lotes.forEach(function (l) { porCodigo[l.codigo] = l; });
      else porCodigo = inv.lotes;
    }
    lotes.forEach(function (f) {
      var p = f.properties, v = porCodigo[p.codigo];
      if (v) {
        p.estado = CFG.estados[v.estado] ? v.estado : CFG.estadoSinInventario;
        p.m2 = v.m2 != null ? v.m2 : p.m2_dxf;
        p.tipologia = v.tipologia || [];
        p.ejemplo = false;
      } else {
        p.estado = CFG.estadoSinInventario; p.m2 = p.m2_dxf; p.tipologia = p.uso_dxf ? [p.uso_dxf] : []; p.ejemplo = true;
      }
    });
  }

  function visible(p) { return (estadoActivo === "todos" || p.estado === estadoActivo) && (etapaActiva === "todas" || p.etapa === etapaActiva); }
  var OPAC = { disponible: 0.78, reservado: 0.72, vendido: 0.62, no_disponible: 0.32 };
  function estilo(p, activo) {
    var c = (CFG.estados[p.estado] || {}).color || "#999", oculto = !visible(p);
    return {
      color: "#FFFFFF",
      weight: activo ? 3 : 0.9,
      fillColor: c,
      fillOpacity: oculto ? 0.04 : (activo ? 0.95 : (OPAC[p.estado] || 0.6)),
      opacity: oculto ? 0.12 : (activo ? 1 : 0.55)
    };
  }
  function dibujarManzanas(feats) {
    feats.forEach(function (f) {
      var capa = L.geoJSON(f, { pane: "manzanas", interactive: false, style: { color: "#FFFFFF", weight: 1.4, opacity: 0.7, fill: false } }).addTo(map);
      var c = capa.getBounds().getCenter();
      L.marker(c, { pane: "manzanas", interactive: false, icon: L.divIcon({ className: "mz-label", html: "<span>M" + esc(f.properties.manzana) + "</span>", iconSize: [40, 20], iconAnchor: [20, 10] }) }).addTo(map);
    });
  }

  function dibujarLotes() {
    lotes.forEach(function (f) {
      var p = f.properties;
      var capa = L.polygon(f.geometry.coordinates[0].map(aLatLng), estilo(p, false)).addTo(map);
      capa.feature = f;
      capa.bindTooltip(String(p.lote), { permanent: true, direction: "center", className: "lot-label", interactive: false });
      capa.on("click", function (e) { L.DomEvent.stopPropagation(e); abrirLote(p.codigo); });
      var el = capa.getElement();
      if (el) { el.setAttribute("data-codigo", p.codigo); el.setAttribute("data-estado", p.estado); el.setAttribute("data-etapa", p.etapa); el.classList.add("lote"); }
      capas[p.codigo] = capa;
    });
  }

  // Amenidades: solo las rotuladas en el DXF (data/amenidades.geojson)
  function dibujarAmenidades(feats) {
    feats.forEach(function (f) {
      var p = f.properties;
      var html = '<div class="amenity-pin"><div class="ico"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2a6 6 0 0 0-4 10.5A5 5 0 0 0 11 18v4h2v-4a5 5 0 0 0 3-5.5A6 6 0 0 0 12 2z"/></svg></div><div class="txt">' + esc(p.nombre) + "</div></div>";
      L.marker(aLatLng(f.geometry.coordinates), { icon: L.divIcon({ html: html, className: "", iconSize: [110, 62], iconAnchor: [55, 19] }) }).addTo(map)
        .bindPopup("<b>" + esc(p.nombre) + "</b><br>" + esc(p.descripcion || ""));
    });
  }

  // ---------- Filtros y leyenda ----------
  function etapas() { var s = {}; lotes.forEach(function (f) { s[f.properties.etapa] = 1; }); return Object.keys(s).sort(function (a, b) { return parseInt(a.slice(1)) - parseInt(b.slice(1)); }); }
  function conteo(est) { return lotes.filter(function (f) { var p = f.properties; return (est === "todos" || p.estado === est) && (etapaActiva === "todas" || p.etapa === etapaActiva); }).length; }
  function conteoEtapa(et) { return lotes.filter(function (f) { var p = f.properties; return (et === "todas" || p.etapa === et) && (estadoActivo === "todos" || p.estado === estadoActivo); }).length; }
  function chipsEstado() {
    var html = '<button class="chip" data-estado="todos" aria-pressed="' + (estadoActivo === "todos") + '">Todos <span class="n">' + conteo("todos") + "</span></button>";
    Object.keys(CFG.estados).forEach(function (k) {
      html += '<button class="chip" data-estado="' + k + '" aria-pressed="' + (estadoActivo === k) + '"><i class="dot" style="background:' + CFG.estados[k].color + '"></i>' + CFG.estados[k].etiqueta + ' <span class="n">' + conteo(k) + "</span></button>";
    });
    $("#filtros").innerHTML = html;
  }
  function chipsEtapa() {
    var html = '<button class="chip chip--etapa" data-etapa="todas" aria-pressed="' + (etapaActiva === "todas") + '">Todas las etapas <span class="n">' + conteoEtapa("todas") + "</span></button>";
    etapas().forEach(function (e) {
      html += '<button class="chip chip--etapa" data-etapa="' + e + '" aria-pressed="' + (etapaActiva === e) + '">Etapa ' + e.slice(1) + ' <span class="n">' + conteoEtapa(e) + "</span></button>";
    });
    $("#filtrosEtapa").innerHTML = html;
  }
  function dibujarFiltros() {
    chipsEstado(); chipsEtapa();
    $("#filtros").addEventListener("click", function (e) {
      var b = e.target.closest(".chip"); if (!b) return;
      estadoActivo = b.getAttribute("data-estado"); chipsEstado(); chipsEtapa(); repintar();
    });
    $("#filtrosEtapa").addEventListener("click", function (e) {
      var b = e.target.closest(".chip"); if (!b) return;
      etapaActiva = b.getAttribute("data-etapa"); chipsEstado(); chipsEtapa(); repintar();
      var sel = Object.keys(capas).filter(function (c) { return etapaActiva === "todas" || capas[c].feature.properties.etapa === etapaActiva; }).map(function (c) { return capas[c]; });
      if (sel.length) map.flyToBounds(L.featureGroup(sel).getBounds(), { padding: [16, 16], duration: 0.6 });
    });
  }
  function dibujarLeyenda() {
    var html = "<b>Estado</b>";
    Object.keys(CFG.estados).forEach(function (k) { html += '<span><i style="background:' + CFG.estados[k].color + '"></i>' + CFG.estados[k].etiqueta + "</span>"; });
    $("#leyenda").innerHTML = html;
  }
  function repintar() {
    Object.keys(capas).forEach(function (c) { capas[c].setStyle(estilo(capas[c].feature.properties, c === seleccionado)); });
    if (seleccionado && capas[seleccionado]) capas[seleccionado].bringToFront();
  }

  // ---------- Precio (apagado por defecto) ----------
  function precioHtml(p) {
    var pr = precios[p.codigo];
    if (!CFG.mostrarPrecios || !pr) return '<strong class="precio-consulta">Consultar por WhatsApp</strong>';
    return "<strong>" + dinero(pr.precio_m2) + "/m²</strong><small>Total estimado: " + dinero(pr.precio_m2 * p.m2) + "</small>";
  }

  // ---------- Tarjeta ----------
  function buscar(codigo) { return lotes.filter(function (f) { return f.properties.codigo === codigo; })[0]; }
  function badgeEstado(p) {
    var e = CFG.estados[p.estado] || { etiqueta: p.estado, color: "#999" };
    return '<span class="estado" style="background:' + e.color + '22;color:' + (p.estado === "reservado" ? "#B45309" : e.color) + '"><i class="dot" style="width:8px;height:8px;border-radius:50%;background:' + e.color + '"></i>' + e.etiqueta + ejTag(p) + "</span>";
  }
  function tagsHtml(t) { return (t || []).map(function (x) { return '<span class="tag">' + esc(x) + "</span>"; }).join(""); }
  function abrirLote(codigo) {
    var f = buscar(codigo); if (!f) return;
    var p = f.properties;
    seleccionado = codigo; repintar();
    $("#cardBody").innerHTML =
      '<div class="fila"><h2 id="cardCodigo">Lote ' + esc(p.codigo) + "</h2>" + badgeEstado(p) + "</div>" +
      '<div class="datos"><div class="dato"><small>Área</small><strong>' + num(p.m2) + " m²</strong>" + ejTag(p) + "</div>" +
      '<div class="dato"><small>Precio</small>' + precioHtml(p) + "</div></div>" +
      '<div class="tags"><span class="tag">Etapa ' + esc(p.etapa.slice(1)) + '</span><span class="tag">Manzana ' + esc(p.manzana) + "</span>" + tagsHtml(p.tipologia) + "</div>" +
      '<div class="acciones"><button id="btnFicha" class="btn btn--ghost" type="button">Ver ficha</button>' +
      '<a id="btnWA" class="btn btn--wa" href="' + linkWhatsApp(p.codigo) + '" target="_blank" rel="noopener">' + icoWA + "WhatsApp</a></div>" +
      (p.ejemplo ? '<p class="nota">Lote sin inventario confirmado: consulte disponibilidad por WhatsApp.</p>' : "");
    $("#card").hidden = false;
    $("#btnFicha").addEventListener("click", function () { abrirFicha(codigo); });
  }
  function cerrarCard() { $("#card").hidden = true; seleccionado = null; if (map) repintar(); }
  $("#cardCerrar").addEventListener("click", cerrarCard);

  // ---------- Ficha ----------
  function miniPlano(f) {
    var pts = f.geometry.coordinates[0], k = Math.cos(pts[0][1] * Math.PI / 180);
    var xs = pts.map(function (p) { return p[0] * k; }), ys = pts.map(function (p) { return p[1]; });
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs), miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    var w = maxx - minx || 1e-9, h = maxy - miny || 1e-9, s = Math.min(200 / w, 140 / h);
    var d = pts.map(function (p, i) { return (i ? "L" : "M") + ((p[0] * k - minx) * s + 10).toFixed(1) + " " + ((maxy - p[1]) * s + 10).toFixed(1); }).join(" ") + "Z";
    var c = (CFG.estados[f.properties.estado] || {}).color || "#999";
    return '<svg width="' + (w * s + 20).toFixed(0) + '" height="' + (h * s + 20).toFixed(0) + '"><path d="' + d + '" fill="' + c + '" fill-opacity=".8" stroke="' + CFG.marca.colores.secundario + '" stroke-width="2"/></svg>';
  }
  function abrirFicha(codigo) {
    var f = buscar(codigo), p = f.properties, pr = precios[p.codigo];
    var filasPrecio = (CFG.mostrarPrecios && pr)
      ? "<tr><td>Precio por m²</td><td>" + dinero(pr.precio_m2) + "</td></tr><tr><td>Total estimado (m² × precio)</td><td>" + dinero(pr.precio_m2 * p.m2) + " <span class=\"ej\">estimado</span></td></tr>"
      : "<tr><td>Precio</td><td>Consultar por WhatsApp</td></tr>";
    $("#fichaBody").innerHTML =
      '<h2 id="fichaTitulo">Lote ' + esc(p.codigo) + "</h2>" + badgeEstado(p) +
      '<div class="ficha-plano">' + miniPlano(f) + "</div>" +
      '<table class="tabla">' +
      "<tr><td>Proyecto</td><td>" + esc(CFG.proyecto.nombre) + "</td></tr>" +
      "<tr><td>Etapa</td><td>" + esc(p.etapa.slice(1)) + "</td></tr>" +
      "<tr><td>Manzana</td><td>" + esc(p.manzana) + "</td></tr>" +
      "<tr><td>Lote</td><td>" + esc(p.lote) + "</td></tr>" +
      "<tr><td>Área</td><td>" + num(p.m2) + " m² " + ejTag(p) + "</td></tr>" +
      (p.tipologia && p.tipologia.length ? "<tr><td>Tipología</td><td>" + esc(p.tipologia.join(", ")) + "</td></tr>" : "") +
      filasPrecio + "</table>" +
      '<a class="btn btn--wa btn--block" href="' + linkWhatsApp(p.codigo) + '" target="_blank" rel="noopener">' + icoWA + "Escribir por WhatsApp</a>" +
      '<p class="aviso-geo">Contorno del lote referencial. Medidas oficiales según plano aprobado.</p>';
    $("#ficha").hidden = false;
  }
  $("#ficha").addEventListener("click", function (e) { if (e.target.hasAttribute("data-cerrar")) $("#ficha").hidden = true; });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { if (!$("#ficha").hidden) $("#ficha").hidden = true; else cerrarCard(); } });

  window.Masterplan = { mapa: function () { return map; }, abrirLote: abrirLote, linkWhatsApp: linkWhatsApp, lotes: function () { return lotes; } };
})();
