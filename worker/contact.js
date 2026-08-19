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
//
// Guardar en D1 y avisar por correo son dos caminos independientes a
// propósito: si uno falla, el otro todavía salva el lead. Sólo se devuelve
// error cuando fallan los dos, que es el único caso en que el dato se pierde.

export async function manejarContacto(request, env) {
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

  const guardado = await guardarEnD1(env, {
    nombre, contacto, empresa, solucion, preferencia, info,
    userAgent: request.headers.get('user-agent') || '',
    ip: request.headers.get('cf-connecting-ip') || '',
  });

  const avisado = await avisarPorCorreo(env, {
    nombre, contacto, empresa, solucion, preferencia, info,
  });

  if (!guardado && !avisado) {
    return json({ ok: false, error: 'db_error' }, 500);
  }

  return json({ ok: true });
}

async function guardarEnD1(env, lead) {
  if (!env.DB) {
    console.error('contact: falta el binding DB (D1) en el proyecto de Pages');
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
    // _work/d1/schema.sql). Se ve en Cloudflare → Pages → Functions → Logs.
    console.error('contact: fallo al guardar en D1:', err && err.message);
    return false;
  }
}

async function avisarPorCorreo(env, lead) {
  if (!env.RESEND_API_KEY) {
    console.error('contact: falta RESEND_API_KEY, no se manda aviso por correo');
    return false;
  }
  try {
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
        reply_to: lead.contacto,
        subject: `Nuevo contacto: ${lead.nombre}${lead.empresa ? ' — ' + lead.empresa : ''}`,
        text:
          `Nombre: ${lead.nombre}\n` +
          `Contacto: ${lead.contacto}\n` +
          `Empresa: ${lead.empresa || '—'}\n` +
          `Solución solicitada: ${lead.solucion}\n` +
          `Prefiere que le contacten por: ${lead.preferencia || '—'}\n` +
          `Más información: ${lead.info || '—'}\n`,
      }),
    });

    if (!res.ok) {
      // Resend explica el motivo en el cuerpo (dominio sin verificar, API key
      // inválida, destinatario no permitido...). Sin esto el fallo es invisible.
      console.error('contact: Resend respondió', res.status, await res.text());
      return false;
    }
    return true;
  } catch (err) {
    console.error('contact: no se pudo llamar a Resend:', err && err.message);
    return false;
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
