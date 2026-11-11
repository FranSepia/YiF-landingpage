// Maneja el POST del formulario de contacto de site/contacto.html.
// Lo llama worker/index.js cuando entra un POST a /api/contact.
//
// Este sitio corre como **Worker con assets estáticos**, no como Cloudflare
// Pages. Por eso la lógica vive aquí y no en una carpeta `functions/`: esa
// convención (un archivo por ruta) es exclusiva de Pages. Mientras el código
// estuvo escrito como Pages Function, /api/contact devolvía 404 pasara lo que
// pasara, porque en un Worker nadie lee esa carpeta.
//
// Bindings y variables (wrangler.jsonc + Settings → Variables and Secrets):
//   DB              (D1) — tabla `leads`, ver _work/d1/schema.sql
//   RESEND_API_KEY  (Secret) — sin ella no se manda correo
//   NOTIFY_TO       (var) — a quién avisar
//   NOTIFY_FROM     (var) — remitente; ojo, Resend exige dominio verificado
//   DIAG_TOKEN      (Secret, opcional) — habilita la respuesta de diagnóstico
//
// Guardar en D1 y avisar por correo son dos caminos independientes a
// propósito: si uno falla, el otro todavía salva el lead. Sólo se devuelve
// error cuando fallan los dos, que es el único caso en que el dato se pierde.
//
// ─── QUÉ FILTRA ESTE ARCHIVO, Y POR QUÉ ──────────────────────────────────────
// El endpoint es público y sin sesión: cualquiera puede postearle. Antes lo
// único que lo defendía era el campo trampa, que frena a los bots tontos y a
// nadie más. Lo que hay ahora, en orden de ejecución:
//
//   1. Origen ajeno        -> 403. Corta el envío disparado desde otra web.
//   2. Cuerpo gigante      -> 413. Antes de leerlo, no después.
//   3. Campo trampa        -> 200 fingido, sin guardar.
//   4. Campos obligatorios -> 400.
//   5. Campos largísimos   -> 400. El maxlength del HTML es sólo una pista
//                             para el navegador: quien postea a mano no lo ve.
//   6. Demasiados de una   -> 429, contando por IP en los últimos minutos.
//      misma IP
//
// Ninguno de esos límites estorba a una persona llenando el formulario: los
// topes están por encima de lo que el propio HTML deja escribir.

// Los topes de cada campo. Coinciden con el maxlength="256" del formulario,
// salvo el texto libre, que necesita más aire. El total de una fila queda en
// ~3,5 kB como mucho.
const LIMITES = {
  nombre: 256,
  contacto: 256,
  empresa: 256,
  solucion: 256,
  preferencia: 64,
  info: 2000,
};

// Tope del cuerpo entero, mirado ANTES de parsearlo. 64 kB es de sobra para un
// formulario de seis campos de texto y evita tener que leer en memoria lo que
// a alguien se le ocurra mandar.
const CUERPO_MAX = 64 * 1024;

// Cuántos envíos se aceptan de una misma IP y en cuánto tiempo. Cinco en diez
// minutos deja de sobra para quien se equivoca y reintenta, y corta el goteo
// automatizado.
const MAX_POR_IP = 5;
const VENTANA_MIN = 10;

// De dónde se acepta un envío. El formulario vive en este dominio; un POST con
// Origin de otro sitio es alguien usando el endpoint desde afuera.
const ORIGENES_PROPIOS = new Set([
  'https://www.why-and-if.solutions',
  'https://why-and-if.solutions',
]);

// Un correo de verdad, mirado con el criterio mínimo que sirve: algo, arroba,
// algo, punto, algo. No se valida más que esto a propósito — las direcciones
// raras pero válidas existen, y rechazar un lead bueno es peor que aceptar uno
// con el correo mal escrito, que igual queda guardado en D1.
const CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function esOrigenPropio(request) {
  const origen = request.headers.get('origin');
  // Sin Origin no se rechaza: lo mandan los navegadores en los POST, pero un
  // cliente viejo o una petición de prueba pueden no traerlo, y perder un lead
  // por eso sería peor que el spam que evita. Para lo automatizado está el
  // límite por IP.
  if (!origen) return true;
  if (ORIGENES_PROPIOS.has(origen)) return true;
  // wrangler dev sirve en localhost: sin esto no se puede probar en local.
  try {
    const host = new URL(origen).hostname;
    return host === 'localhost' || host === '127.0.0.1';
  } catch (err) {
    return false;
  }
}

export async function manejarContacto(request, env) {
  if (!esOrigenPropio(request)) {
    return json({ ok: false, error: 'bad_origin' }, 403);
  }

  const largo = Number(request.headers.get('content-length') || 0);
  if (largo > CUERPO_MAX) {
    return json({ ok: false, error: 'too_large' }, 413);
  }

  let form;
  try {
    form = await request.formData();
  } catch (err) {
    return json({ ok: false, error: 'invalid_form' }, 400);
  }

  // Campo trampa para bots (ver assets/contacto/js/contact-form.js). Si viene
  // lleno, un humano nunca lo habría tocado: respondemos éxito sin guardar nada.
  if ((form.get('website') || '').toString().trim()) {
    return json({ ok: true });
  }

  const nombre = (form.get('name') || '').toString().trim();
  const contacto = (form.get('email') || '').toString().trim();
  const solucion = (form.get('Solucipon-Solicitada') || '').toString().trim();
  const preferencia = (form.get('pref') || '').toString().trim();
  const empresa = (form.get('Empresa') || '').toString().trim();
  const info = (form.get('M-s-Informaci-n') || '').toString().trim();

  if (!nombre || !contacto || !solucion) {
    return json({ ok: false, error: 'missing_fields' }, 400);
  }

  const lead = { nombre, contacto, empresa, solucion, preferencia, info };
  const largoDeMas = Object.keys(LIMITES).find(k => lead[k].length > LIMITES[k]);
  if (largoDeMas) {
    return json({ ok: false, error: 'too_long', campo: largoDeMas }, 400);
  }

  const ip = request.headers.get('cf-connecting-ip') || '';
  if (await vieneMuySeguido(env, ip)) {
    return json({ ok: false, error: 'rate_limited' }, 429, {
      'Retry-After': String(VENTANA_MIN * 60),
    });
  }

  const guardado = await guardarEnD1(env, {
    ...lead,
    userAgent: request.headers.get('user-agent') || '',
    ip,
  });

  const aviso = await avisarPorCorreo(env, lead);

  if (!guardado && !aviso.ok) {
    return json({ ok: false, error: 'db_error' }, 500);
  }

  // Respuesta de diagnóstico: dice por qué falló el correo sin tener que ir a
  // buscar los logs del dashboard. Va detrás de un secreto porque el detalle
  // incluye lo que conteste Resend (dominio sin verificar, clave inválida,
  // destinatario no permitido), y eso es información del estado interno que no
  // le corresponde a cualquiera que postee. Sin DIAG_TOKEN configurado, no
  // existe: el `diag=1` de antes lo contestaba a quien lo pidiera.
  const diag = (form.get('diag') || '').toString();
  if (env.DIAG_TOKEN && diag && diag === env.DIAG_TOKEN) {
    return json({ ok: true, guardado, mail: aviso });
  }

  return json({ ok: true });
}

// Cuántos envíos lleva esta IP en la ventana. Se apoya en la propia tabla de
// leads en vez de sumar un almacén nuevo: la fila ya se guarda con ip y
// created_at, y el índice por created_at ya existe.
//
// Si la consulta falla (tabla ausente, D1 caído) se deja pasar a propósito:
// ante la duda es mejor aceptar un lead de más que perder uno bueno por una
// falla de la base. El spam que eso deja entrar lo frena el resto del filtro.
async function vieneMuySeguido(env, ip) {
  if (!env.DB || !ip) return false;
  try {
    const fila = await env.DB.prepare(
      `SELECT COUNT(*) AS n FROM leads
        WHERE ip = ?1 AND created_at > datetime('now', ?2)`
    )
      .bind(ip, `-${VENTANA_MIN} minutes`)
      .first();
    return Number(fila && fila.n) >= MAX_POR_IP;
  } catch (err) {
    console.error('contact: no se pudo contar envíos recientes:', err && err.message);
    return false;
  }
}

async function guardarEnD1(env, lead) {
  if (!env.DB) {
    console.error('contact: falta el binding DB (D1)');
    return false;
  }
  try {
    await env.DB.prepare(
      `INSERT INTO leads (nombre, contacto, empresa, solucion, preferencia, info, user_agent, ip)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
      .bind(
        lead.nombre,
        lead.contacto,
        lead.empresa,
        lead.solucion,
        lead.preferencia,
        lead.info,
        lead.userAgent,
        lead.ip
      )
      .run();
    return true;
  } catch (err) {
    // Lo más común aquí: la tabla `leads` no existe todavía (falta aplicar
    // _work/d1/schema.sql). Se ve en Cloudflare → Worker → Logs.
    console.error('contact: fallo al guardar en D1:', err && err.message);
    return false;
  }
}

async function avisarPorCorreo(env, lead) {
  if (!env.RESEND_API_KEY) {
    console.error('contact: falta RESEND_API_KEY, no se manda aviso por correo');
    return { ok: false, detalle: 'falta RESEND_API_KEY' };
  }
  try {
    // El campo se llama "contacto" y acepta teléfono, así que no siempre es un
    // correo. Sólo se pone como reply_to cuando lo es: con una dirección
    // inválida Resend rechaza el envío entero y el aviso se pierde, y además
    // ese campo lo escribe un desconocido, así que no conviene que cualquier
    // texto termine siendo la dirección a la que contesta tu bandeja.
    const responderA = CORREO.test(lead.contacto) ? lead.contacto : null;

    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: env.NOTIFY_FROM || 'Y&iF Web <onboarding@resend.dev>',
        to: [env.NOTIFY_TO || 'contacto@why-and-if.solutions'],
        // Responder al correo contesta directo al prospecto, no a la web.
        ...(responderA ? { reply_to: responderA } : {}),
        subject: `Nuevo contacto: ${lead.nombre}${lead.empresa ? ' — ' + lead.empresa : ''}`,
        text:
          `Nombre: ${lead.nombre}\n` +
          `Contacto: ${lead.contacto}\n` +
          `Empresa: ${lead.empresa || '—'}\n` +
          `Solución solicitada: ${lead.solucion}\n` +
          `Prefiere que le contacten por: ${lead.preferencia || '—'}\n` +
          `Más información: ${lead.info || '—'}\n` +
          (responderA ? '' : '\n(El contacto no es un correo, así que este aviso no lleva respuesta directa.)\n'),
      }),
    });

    if (!res.ok) {
      // Resend explica el motivo en el cuerpo (dominio sin verificar, API key
      // inválida, destinatario no permitido...). Sin esto el fallo es invisible.
      const cuerpo = await res.text();
      console.error('contact: Resend respondió', res.status, cuerpo);
      return { ok: false, detalle: `HTTP ${res.status} ${cuerpo}`.slice(0, 300) };
    }
    return { ok: true, detalle: 'enviado' };
  } catch (err) {
    console.error('contact: no se pudo llamar a Resend:', err && err.message);
    return { ok: false, detalle: 'excepcion: ' + (err && err.message) };
  }
}

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}
