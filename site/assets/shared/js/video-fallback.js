/*
Y&iF — Videos de fondo: reproducir si se puede, y si no, quedar como imagen.

El problema: en iOS con Modo de Bajo Consumo activado (y en Android con el
Ahorro de datos), el navegador bloquea el autoplay AUNQUE el video esté muteado.
Cuando eso pasa, iOS dibuja encima un botón de play que se ve mal en un video
que es puramente decorativo.

Qué hace este script, en orden:
  1. Intenta reproducir cada video al cargar.
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

    function reintentar() {
      videos.forEach(function (v) { if (v.paused) intentarPlay(v); });
    }

    reintentar();

    // Segunda oportunidad: la primera interacción del usuario suele desbloquear.
    ['touchstart', 'pointerdown', 'click', 'scroll', 'keydown'].forEach(function (ev) {
      window.addEventListener(ev, reintentar, { once: true, passive: true });
    });

    window.setTimeout(function () {
      videos.forEach(function (v) {
        // HAVE_CURRENT_DATA(2) o más significa que sí hay imagen que mostrar.
        if (v.paused && v.readyState < 2) return convertirEnImagen(v);
        if (v.paused) convertirEnImagen(v);
      });
    }, GRACIA_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
