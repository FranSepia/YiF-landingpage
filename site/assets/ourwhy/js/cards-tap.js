/*
Y&iF — "Lo que nos mueve": abrir las tarjetas al tocarlas.

Contexto de por qué está escrito así:

1. El diseño original revela el texto con `:hover`. En un teléfono no hay
   hover: iOS lo simula tras el primer toque, pero se queda pegado en una
   tarjeta y las demás no abren nunca. De ahí que sólo "Our Why" mostrara su
   texto.

2. Este script sólo pone y quita la clase `is-open`. Todo lo visual (mostrar
   el párrafo, crecer de alto, oscurecer el video) vive en
   assets/shared/css/mobile-fixes.css dentro de @media (max-width:767px).
   Antes se aplicaban estilos inline desde aquí, y al cerrar quedaban restos
   que dejaban el texto medio asomado; con una sola clase el estado siempre
   es o abierto o cerrado, sin términos medios.

3. Ninguna tarjeta arranca abierta: al cargar sólo se ven los tres títulos.
*/
(function () {
  'use strict';

  var MAX_ANCHO = 767;

  function abrir(tarjeta, abierta) {
    tarjeta.classList.toggle('is-open', abierta);
    tarjeta.setAttribute('aria-expanded', abierta ? 'true' : 'false');
  }

  // Si la tarjeta abierta crece más que la pantalla, el final del texto queda
  // fuera de vista y parece que está cortado. Se acerca lo justo para leerlo.
  function acercar(tarjeta) {
    window.setTimeout(function () {
      var caja = tarjeta.getBoundingClientRect();
      var alto = window.innerHeight || document.documentElement.clientHeight;
      if (caja.bottom > alto || caja.top < 0) {
        tarjeta.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 60);
  }

  function iniciar() {
    if (window.innerWidth > MAX_ANCHO) return;

    var tarjetas = Array.prototype.slice.call(
      document.querySelectorAll('.benefits_card_wrap')
    );
    if (!tarjetas.length) return;

    tarjetas.forEach(function (tarjeta) {
      // Sin esto, iOS Safari no entrega eventos de clic en un <div> normal.
      tarjeta.style.cursor = 'pointer';
      tarjeta.setAttribute('tabindex', '0');
      tarjeta.setAttribute('role', 'button');
      abrir(tarjeta, false);

      var yaManejado = false;

      function alternar(e) {
        if (e.target.closest && e.target.closest('a')) return; // respeta enlaces
        if (yaManejado) return;                                // evita doble disparo
        yaManejado = true;
        window.setTimeout(function () { yaManejado = false; }, 350);

        var estaAbierta = tarjeta.classList.contains('is-open');
        tarjetas.forEach(function (t) { abrir(t, false); });
        if (!estaAbierta) {
          abrir(tarjeta, true);
          acercar(tarjeta);
        }
      }

      // touchend y click: iOS a veces sólo entrega uno de los dos.
      tarjeta.addEventListener('touchend', alternar);
      tarjeta.addEventListener('click', alternar);
      tarjeta.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); alternar(e); }
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
