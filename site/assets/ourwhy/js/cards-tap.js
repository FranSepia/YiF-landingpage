/*
Y&iF — "Lo que nos mueve": abrir las tarjetas al tocarlas.

El diseño original revela el texto con `:hover`. En un teléfono no hay hover:
iOS lo simula tras el primer toque, pero de forma inconsistente (se queda
pegado en una tarjeta y las demás nunca abren). De ahí que sólo "Our Why"
mostrara su texto.

Este script añade la clase `is-open` a la tarjeta tocada y se la quita a las
demás, para que abrir/cerrar sea explícito y predecible. El CSS que responde a
`.is-open` está en shared/css/mobile-fixes.css.

Sólo se activa en pantallas táctiles angostas: en escritorio el hover original
sigue mandando, sin tocar nada.
*/
(function () {
  'use strict';

  var MAX_ANCHO = 767;

  function esTactil() {
    return window.matchMedia('(hover: none)').matches || 'ontouchstart' in window;
  }

  function iniciar() {
    if (window.innerWidth > MAX_ANCHO || !esTactil()) return;

    var tarjetas = Array.prototype.slice.call(
      document.querySelectorAll('.benefits_card_wrap')
    );
    if (!tarjetas.length) return;

    tarjetas.forEach(function (tarjeta) {
      // accesible con teclado además de con el dedo
      tarjeta.setAttribute('tabindex', '0');
      tarjeta.setAttribute('role', 'button');

      function alternar(e) {
        // no interceptar toques sobre enlaces reales dentro de la tarjeta
        if (e.target.closest && e.target.closest('a')) return;
        var abierta = tarjeta.classList.contains('is-open');
        tarjetas.forEach(function (t) { t.classList.remove('is-open'); });
        if (!abierta) tarjeta.classList.add('is-open');
      }

      tarjeta.addEventListener('click', alternar);
      tarjeta.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); alternar(e); }
      });
    });

    // La primera abierta por defecto, para que se vea que son desplegables.
    tarjetas[0].classList.add('is-open');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
