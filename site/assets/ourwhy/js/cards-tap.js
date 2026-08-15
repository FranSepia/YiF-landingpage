/*
Y&iF — "Lo que nos mueve": abrir las tarjetas al tocarlas.

Contexto de por qué está escrito así:

1. El diseño original revela el texto con `:hover`. En un teléfono no hay
   hover: iOS lo simula tras el primer toque, pero se queda pegado en una
   tarjeta y las demás no abren nunca. De ahí que sólo "Our Why" mostrara su
   texto.

2. El colapso se hace con `grid-template-rows: 0fr -> 1fr`. Safari trata las
   filas `fr` de tamaño cero distinto que Chrome, así que aunque la clase se
   aplicara, el texto seguía sin verse en el iPhone.

Por eso este script no se conforma con poner una clase: aplica los estilos
directamente sobre los elementos (inline, con prioridad `important`). Así
funciona aunque alguna hoja de estilos posterior intente pisarlos, que es
justo lo que no se podía descartar depurando a ciegas sobre un iPhone.
*/
(function () {
  'use strict';

  var MAX_ANCHO = 767;

  function abrir(tarjeta, abierta) {
    tarjeta.classList.toggle('is-open', abierta);

    var wrap = tarjeta.querySelector('.benefits_card_mask_wrap');
    var clip = tarjeta.querySelector('.benefits_card_mask_clip');
    var texto = tarjeta.querySelector('.benefits_card_text');

    if (wrap) {
      if (abierta) {
        // display:block saca el bloque del grid: así el 0fr deja de aplicar.
        wrap.style.setProperty('display', 'block', 'important');
        wrap.style.setProperty('grid-template-rows', '1fr', 'important');
      } else {
        wrap.style.removeProperty('display');
        wrap.style.removeProperty('grid-template-rows');
      }
    }
    if (clip) {
      if (abierta) {
        clip.style.setProperty('overflow', 'visible', 'important');
        clip.style.setProperty('height', 'auto', 'important');
        clip.style.setProperty('max-height', 'none', 'important');
      } else {
        clip.style.removeProperty('overflow');
        clip.style.removeProperty('height');
        clip.style.removeProperty('max-height');
      }
    }
    if (texto) {
      if (abierta) {
        texto.style.setProperty('display', 'block', 'important');
        texto.style.setProperty('height', 'auto', 'important');
        texto.style.setProperty('opacity', '1', 'important');
        texto.style.setProperty('visibility', 'visible', 'important');
      } else {
        texto.style.removeProperty('display');
        texto.style.removeProperty('height');
        texto.style.removeProperty('opacity');
        texto.style.removeProperty('visibility');
      }
    }
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

      var yaManejado = false;

      function alternar(e) {
        if (e.target.closest && e.target.closest('a')) return; // respeta enlaces
        if (yaManejado) return;                                // evita doble disparo
        yaManejado = true;
        window.setTimeout(function () { yaManejado = false; }, 350);

        var estaAbierta = tarjeta.classList.contains('is-open');
        tarjetas.forEach(function (t) { abrir(t, false); });
        if (!estaAbierta) abrir(tarjeta, true);
      }

      // touchend y click: iOS a veces sólo entrega uno de los dos.
      tarjeta.addEventListener('touchend', alternar);
      tarjeta.addEventListener('click', alternar);
      tarjeta.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); alternar(e); }
      });
    });

    // La primera abierta, para que se note que son desplegables.
    abrir(tarjetas[0], true);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
