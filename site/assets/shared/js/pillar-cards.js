/*
 * Tarjetas de los pilares (página de Metodología).
 *
 * Dos problemas que resuelve:
 *
 * 1. Se abrían sólo con :hover, así que al quitar el cursor se cerraban de
 *    golpe. Ahora la última tocada se queda abierta hasta que se señala otra:
 *    el bloque nunca "parpadea" entre abierta y cerrada.
 *
 * 2. Al abrirse, la tarjeta crecía y empujaba el pie de página hasta 500px
 *    hacia abajo. Aquí se mide de antemano cuánto ocupa la más alta ya abierta
 *    y se reserva ese alto, así el pie no se mueve al pasar de una a otra.
 */
(function () {
  'use strict';

  var OPEN = 'is-open';
  var MEASURING = 'yf-measuring';

  function init() {
    var layout = document.querySelector('.benefits_layoutf');
    if (!layout) return;

    var cards = [].slice.call(layout.querySelectorAll('.benefits_card_wrapf'));
    if (!cards.length) return;

    function openOnly(card) {
      cards.forEach(function (c) {
        c.classList.toggle(OPEN, c === card);
      });
    }

    cards.forEach(function (card) {
      // mouseenter no burbujea: se dispara una sola vez por tarjeta.
      card.addEventListener('mouseenter', function () { openOnly(card); });
      // En pantallas táctiles no hay hover; el toque hace lo mismo.
      card.addEventListener('click', function () { openOnly(card); });
      card.addEventListener('focusin', function () { openOnly(card); });
    });

    // --- Reserva de alto -----------------------------------------------
    // Se abre cada tarjeta por turnos (sin animación, para medir el tamaño
    // final y no uno intermedio) y se guarda el alto mayor.
    function reserveHeight() {
      var open = layout.querySelector('.' + OPEN);

      layout.style.minHeight = '';
      layout.classList.add(MEASURING);

      var tallest = 0;
      cards.forEach(function (card) {
        openOnly(card);
        // Lectura forzada para que el navegador aplique el cambio ya.
        void layout.offsetHeight;
        tallest = Math.max(tallest, layout.getBoundingClientRect().height);
      });

      // Se deja como estaba antes de medir.
      cards.forEach(function (c) { c.classList.remove(OPEN); });
      if (open) open.classList.add(OPEN);
      void layout.offsetHeight;
      layout.classList.remove(MEASURING);

      layout.style.minHeight = Math.ceil(tallest) + 'px';
    }

    reserveHeight();

    // Arranca con la primera abierta: como el alto ya está reservado para la
    // más grande, si ninguna lo estuviera quedaría un hueco vacío enorme
    // debajo de las tres. Así ese espacio se usa desde el principio.
    if (!layout.querySelector('.' + OPEN)) openOnly(cards[0]);

    // Las fuentes cambian el alto del texto al terminar de cargar.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(reserveHeight).catch(function () {});
    }

    var t;
    window.addEventListener('resize', function () {
      clearTimeout(t);
      t = setTimeout(reserveHeight, 200);
    });

    // El texto de las tarjetas cambia de idioma con el botón ES/EN, y el
    // inglés no ocupa lo mismo que el español.
    document.addEventListener('yf:langchange', function () {
      setTimeout(reserveHeight, 60);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
