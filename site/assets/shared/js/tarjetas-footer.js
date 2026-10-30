/* Footer de las tarjetas digitales (site/tarjetas/*.html).
 *
 * El layout de las tarjetas viene de Webflow y está armado con posiciones
 * absolutas y medidas fijas por breakpoint. El footer estaba pegado al fondo
 * de la ventana (bottom:0), no al final del contenido: en una pantalla baja
 * el fondo de la ventana cae por encima de los paneles y el footer terminaba
 * encimado sobre ellos.
 *
 * Aquí lo colocamos midiendo dónde termina de verdad la tarjeta y poniéndolo
 * debajo. Si no cabe en la pantalla, hay que bajar para verlo; si cabe, se
 * queda al pie como antes.
 */
(function () {
  'use strict';

  var SEPARACION = 28; // aire entre la tarjeta y el footer
  var MARGEN = 24;     // aire debajo del footer

  // .section-28 es el footer de la tarjeta de la empresa. data-tarjeta-footer
  // queda para cualquier tarjeta nueva que no reuse esa clase de Webflow.
  var footer = document.querySelector('[data-tarjeta-footer], .section-28');
  if (!footer) return;

  function colocar() {
    // Mientras medimos, el footer no debe contarse a sí mismo, y el alto que
    // le pusimos al body en la pasada anterior tampoco: así la medición da lo
    // mismo se llame una vez o diez.
    footer.style.position = 'absolute';
    footer.style.left = '0';
    footer.style.right = '0';
    footer.style.bottom = 'auto';
    footer.style.top = '0px';
    var scroll = window.scrollY;
    document.body.style.minHeight = '';

    var cuerpo = document.body.getBoundingClientRect();
    // El bloque contenedor de un absoluto hijo del body es su caja de relleno.
    var origen = cuerpo.top + parseFloat(getComputedStyle(document.body).borderTopWidth || 0);

    // Dónde termina lo que se ve. Recorremos todo porque los paneles están
    // posicionados a mano y algunos se salen de su contenedor.
    var nodos = document.body.querySelectorAll('*');
    var fijos = [];
    var fin = 0;
    for (var i = 0; i < nodos.length; i++) {
      var el = nodos[i];
      if (el === footer || footer.contains(el)) continue;
      // El fondo de acuarela va en un div fijo que cubre la pantalla, con un
      // canvas dentro: no es contenido y además crece con el body, así que
      // mediríamos en círculo. (El body lleva transform-style:preserve-3d,
      // por eso ese fixed se mide contra el body y no contra la ventana.)
      // Los nodos vienen en orden de documento, así que el padre fijo ya está
      // en la lista cuando llegamos a sus hijos.
      if (getComputedStyle(el).position === 'fixed') { fijos.push(el); continue; }
      var saltar = false;
      for (var j = 0; j < fijos.length; j++) {
        if (fijos[j].contains(el)) { saltar = true; break; }
      }
      if (saltar) continue;
      var r = el.getBoundingClientRect();
      if (!r.width && !r.height) continue;
      var abajo = r.bottom - origen;
      if (abajo > fin) fin = abajo;
    }

    var alto = footer.offsetHeight;
    var pie = Math.round(window.innerHeight - alto);
    // Debajo del contenido, pero nunca más arriba del pie de la ventana:
    // en pantallas altas se queda donde estaba y no abre un hueco.
    var arriba = Math.max(Math.round(fin) + SEPARACION, pie);

    footer.style.top = arriba + 'px';
    // Sólo alargamos la página cuando el footer quedó debajo de la tarjeta;
    // si va al pie de la ventana, el body ya mide lo suficiente y así no
    // aparece una barra de scroll de unos pocos píxeles.
    document.body.style.minHeight = arriba > pie ? (arriba + alto + MARGEN) + 'px' : '';
    if (window.scrollY !== scroll) window.scrollTo(window.scrollX, scroll);
  }

  var pendiente = 0;
  function recolocar() {
    if (pendiente) return;
    pendiente = requestAnimationFrame(function () {
      pendiente = 0;
      colocar();
    });
  }

  // En los momentos en que cambia el contenido medimos de inmediato: con
  // requestAnimationFrame la pestaña en segundo plano puede tardar en darnos
  // el turno y el footer se quedaría donde estaba.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', colocar);
  } else {
    colocar();
  }
  // El video de fondo y las tipografías cambian la altura al terminar de cargar.
  window.addEventListener('load', colocar);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(colocar);
  // Al redimensionar sí conviene espaciar las mediciones.
  window.addEventListener('resize', recolocar);
  window.addEventListener('orientationchange', recolocar);
})();
