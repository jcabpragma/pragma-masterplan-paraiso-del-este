/* Lista de proyectos del sitio. Para agregar uno: crear proyectos/<id>/config.js y añadirlo aquí. */
window.MASTERPLAN_PROYECTOS = [
  { id: "pde", sigla: "PDE", nombre: "Paraíso del Este" },
  { id: "sde", sigla: "SDE", nombre: "Samanes del Este" }
];
(function () {
  var p = (new URLSearchParams(location.search).get("p") || "pde").toLowerCase();
  if (!window.MASTERPLAN_PROYECTOS.some(function (x) { return x.id === p; })) p = "pde";
  window.MASTERPLAN_ID = p;
  document.write('<script src="proyectos/' + p + '/config.js"><\/script>');
})();
