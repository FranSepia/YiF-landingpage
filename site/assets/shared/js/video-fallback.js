/*
Y&iF — Videos de fondo: reproducir si se puede, y si no, quedar como imagen.

El problema: en iOS con Modo de Bajo Consumo activado (y en Android con el
Ahorro de datos), el navegador bloquea el autoplay AUNQUE el video esté muteado.
Cuando eso pasa, iOS dibuja encima un botón de play que se ve mal en un video
que es puramente decorativo.

Qué hace este script, en orden:
  1. Intenta reproducir cada video al cargar (o, si lleva data-yf-lazy, cuando
     se acerca a la pantalla).
  2. Si falló, lo reintenta en cuanto el usuario toca o hace scroll — muchos
     navegadores liberan el autoplay tras la primera interacción real.
  3. Si después de la ventana de gracia sigue sin arrancar, quita el <video> y
     deja en su lugar el poster como imagen de fondo. Sin botón de play, sin
     hueco negro: se ve como una foto y ya.

El poster se toma de `data-poster-url` del contenedor de Webflow y, si no está,
del background-image que el propio <video> trae en su atributo style.
*/
(function () {
  'use strict';

  var GRACIA_MS = 4000; // margen para conexiones lentas antes de rendirse

  function posterDe(video) {
    var wrap = video.closest ? video.closest('.w-background-video') : video.parentElement;
    if (wrap) {
      var attr = wrap.getAttribute('data-poster-url');
      if (attr) return { url: attr, wrap: wrap };
    }
    var bg = video.style.backgroundImage || '';
    var m = bg.match(/url\(\s*["']?(.+?)["']?\s*\)/);
    if (m) return { url: m[1], wrap: wrap || video.parentElement };
    return null;
  }

  function convertirEnImagen(video) {
    var poster = posterDe(video);
    // Sin poster no hay nada mejor que mostrar: se deja el video como está.
    if (!poster || !poster.wrap) return;
    poster.wrap.style.backgroundImage = 'url("' + poster.url + '")';
    poster.wrap.style.backgroundSize = 'cover';
    poster.wrap.style.backgroundPosition = 'center';
    poster.wrap.style.backgroundRepeat = 'no-repeat';
    video.style.display = 'none'; // esto es lo que elimina el botón de play
  }

  function intentarPlay(video) {
    try {
      var p = video.play();
      if (p && typeof p.catch === 'function') p.catch(function () { /* bloqueado */ });
    } catch (e) { /* navegador viejo */ }
  }

  function iniciar() {
    var videos = Array.prototype.slice.call(document.querySelectorAll('video'));
    if (!videos.length) return;

    // Los que llevan data-yf-lazy vienen sin autoplay y con preload="none":
    // no se descargan hasta acercarse a la pantalla (en "Lo que nos mueve" son
    // ~9 MB que antes bajaban todos al abrir la página). El resto arranca ya.
    var activos = [];

    function activar(v) {
      if (activos.indexOf(v) !== -1) return;
      activos.push(v);
      intentarPlay(v);
      // La ventana de gracia corre desde que el video empieza a cargar, no
      // desde que cargó la página: uno que entra tarde en pantalla no debe
      // quedarse como imagen sin haber tenido oportunidad.
      window.setTimeout(function () {
        if (v.paused) convertirEnImagen(v);
      }, GRACIA_MS);
    }

    function reintentar() {
      activos.forEach(function (v) { if (v.paused) intentarPlay(v); });
    }

    var perezosos = videos.filter(function (v) { return v.hasAttribute('data-yf-lazy'); });
    videos.forEach(function (v) { if (perezosos.indexOf(v) === -1) activar(v); });

    if (perezosos.length) {
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entradas) {
          entradas.forEach(function (e) {
            if (!e.isIntersecting) return;
            io.unobserve(e.target);
            activar(e.target);
          });
        }, { rootMargin: '300px 0px' });
        perezosos.forEach(function (v) { io.observe(v); });
      } else {
        perezosos.forEach(activar);
      }
    }

    // Segunda oportunidad: la primera interacción del usuario suele desbloquear.
    ['touchstart', 'pointerdown', 'click', 'scroll', 'keydown'].forEach(function (ev) {
      window.addEventListener(ev, reintentar, { once: true, passive: true });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
