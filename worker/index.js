/*
Punto de entrada del Worker que sirve el sitio.

Cómo se reparte el tráfico (ver "assets" en wrangler.jsonc):

1. Todo lo que NO está bajo /assets/ (las páginas, robots.txt, sitemap.xml,
   llms.txt y /api/contact) pasa primero por este script — eso es
   `run_worker_first`. Hace falta para tres cosas que el enrutador de assets
   no sabe hacer solo:
     - mandar con 301 cualquier visita a http:// o al dominio sin www hacia
       https://www.why-and-if.solutions (una sola versión del sitio para
       Google, en vez de cuatro copias);
     - volver permanentes (301) las redirecciones que el enrutador hace como
       temporales (307): /contacto.html → /contacto, /soluciones/ → /soluciones;
     - devolver la página 404.html con status 404 real cuando la URL no existe.
2. Lo que está bajo /assets/ (CSS, JS, imágenes, videos, fuentes) lo sirve el
   enrutador de assets directo, sin pasar por aquí: así no se gasta una
   invocación del Worker por cada imagen.
*/
import { manejarContacto } from './contact.js';

const HOST_CANONICO = 'www.why-and-if.solutions';
const HOSTS_PROPIOS = new Set(['why-and-if.solutions', HOST_CANONICO]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // En local (wrangler dev) el host es 127.0.0.1/localhost y no se toca.
    if (HOSTS_PROPIOS.has(url.hostname) &&
        (url.protocol !== 'https:' || url.hostname !== HOST_CANONICO)) {
      url.protocol = 'https:';
      url.hostname = HOST_CANONICO;
      url.port = '';
      // 308 en vez de 301 para POST: un 301 convierte el POST en GET y el
      // formulario llegaría vacío.
      const esLectura = request.method === 'GET' || request.method === 'HEAD';
      return Response.redirect(url.toString(), esLectura ? 301 : 308);
    }

    if (url.pathname === '/api/contact') {
      if (request.method !== 'POST') {
        return new Response('Method Not Allowed', {
          status: 405,
          headers: { Allow: 'POST' },
        });
      }
      return manejarContacto(request, env);
    }

    const respuesta = await env.ASSETS.fetch(request);

    // El enrutador de assets normaliza las URLs (quita .html y la / final)
    // con 307, que para Google significa "temporal": no consolida la URL.
    if (respuesta.status === 307) {
      const destino = respuesta.headers.get('Location');
      if (destino) {
        return new Response(null, { status: 301, headers: { Location: destino } });
      }
    }

    if (respuesta.status === 404 && (request.method === 'GET' || request.method === 'HEAD')) {
      const pagina = await env.ASSETS.fetch(new URL('/404', url));
      if (pagina.ok) {
        const headers = new Headers(pagina.headers);
        headers.set('Cache-Control', 'no-store');
        return new Response(request.method === 'HEAD' ? null : pagina.body, {
          status: 404,
          headers,
        });
      }
    }

    return respuesta;
  },
};
