/*
 * Menú desplegable para pantallas medianas y chicas.
 *
 * El HTML exportado de Webflow trae data-collapse="medium" en la barra, así
 * que abajo de 991px el CSS de Webflow esconde .w-nav-menu y muestra un
 * .w-nav-button… que el export NUNCA incluyó. Resultado: en tablet, celular o
 * monitor vertical no quedaba ningún menú, sólo el logo.
 *
 * Este script inyecta ese botón que falta y lo conecta. Los estilos viven en
 * assets/shared/css/responsive-fixes.css.
 */
(function () {
  'use strict';

  var BREAKPOINT = 991;

  function init() {
    var wrapper = document.querySelector('.navbar-wrapper.w-nav');
    var container = wrapper && wrapper.querySelector('.navbar-container');
    var menu = wrapper && wrapper.querySelector('.nav-menu.w-nav-menu');
    if (!wrapper || !container || !menu) return;

    // Si algún día el export sí trae el botón de Webflow, no duplicamos.
    if (wrapper.querySelector('.w-nav-button') || wrapper.querySelector('.yf-nav-toggle')) return;

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'yf-nav-toggle';
    toggle.setAttribute('aria-label', 'Abrir menú');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.appendChild(document.createElement('span'));

    // Va al final del contenedor: el logo queda a la izquierda y el botón a la
    // derecha, que es como se lee la barra en desktop.
    container.appendChild(toggle);

    function setOpen(open) {
      wrapper.classList.toggle('yf-nav-open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
    }

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      setOpen(!wrapper.classList.contains('yf-nav-open'));
    });

    // Al elegir un destino se cierra solo.
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    // Tocar fuera cierra el panel.
    document.addEventListener('click', function (e) {
      if (!wrapper.classList.contains('yf-nav-open')) return;
      if (!wrapper.contains(e.target)) setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });

    // Si se agranda la ventana, el menú vuelve a ser horizontal: hay que
    // limpiar el estado abierto o queda un panel colgado en desktop.
    window.addEventListener('resize', function () {
      if (window.innerWidth > BREAKPOINT) setOpen(false);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
