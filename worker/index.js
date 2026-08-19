/*
Punto de entrada del Worker que sirve el sitio.

Cómo se reparte el tráfico (ver "assets" en wrangler.jsonc):

1. Cloudflare intenta primero servir un archivo estático de site/. Si la
   petición coincide con uno, este script ni se ejecuta — así que todas las
   páginas siguen sirviéndose igual de rápido que antes, y las URLs limpias
   (/contacto → contacto.html) las sigue resolviendo el enrutador de assets.
2. Sólo si no hay archivo que coincida, entra este `fetch`. Ahí es donde
   atendemos /api/contact, que no es un archivo sino código.

Por eso no hace falta `run_worker_first`: /api/contact nunca va a existir como
archivo, así que siempre acaba aquí.
*/
import { manejarContacto } from './contact.js';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/api/contact') {
      if (request.method !== 'POST') {
        return new Response('Method Not Allowed', {
          status: 405,
          headers: { Allow: 'POST' },
        });
      }
      return manejarContacto(request, env);
    }

    // Cualquier otra cosa vuelve al enrutador de assets, que devuelve el
    // archivo o el 404 según corresponda. Sin esto, un 404 normal moriría aquí.
    return env.ASSETS.fetch(request);
  },
};
