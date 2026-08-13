// Cloudflare Pages Function — recibe el POST de site/contacto.html.
// Ruta: /api/contact (el nombre del archivo define la ruta).
//
// Bindings esperados en el proyecto de Pages (Settings → Functions):
//   DB              (D1 database binding, obligatorio) — tabla `leads`, ver _work/d1/schema.sql
//   RESEND_API_KEY  (variable de entorno "Secret", opcional) — si falta, solo se guarda en D1
//   NOTIFY_TO       (texto, opcional) — a quién avisar. Default: contacto@why-and-if.solutions
//   NOTIFY_FROM     (texto, opcional) — remitente. Default: onboarding@resend.dev

export async function onRequestPost({ request, env }) {
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

  try {
    await env.DB.prepare(
      `INSERT INTO leads (nombre, contacto, empresa, solucion, preferencia, info, user_agent, ip)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
      .bind(
        nombre,
        contacto,
        empresa,
        solucion,
        preferencia,
        info,
        request.headers.get('user-agent') || '',
        request.headers.get('cf-connecting-ip') || ''
      )
      .run();
  } catch (err) {
    return json({ ok: false, error: 'db_error' }, 500);
  }

  // Aviso por correo: best-effort. Si Resend falla o no está configurado, el
  // lead ya quedó a salvo en D1 — no volteamos la respuesta a error por esto.
  if (env.RESEND_API_KEY) {
    try {
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.RESEND_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from: env.NOTIFY_FROM || 'Y&iF Web <onboarding@resend.dev>',
          to: [env.NOTIFY_TO || 'contacto@why-and-if.solutions'],
          subject: `Nuevo contacto: ${nombre}${empresa ? ' — ' + empresa : ''}`,
          text:
            `Nombre: ${nombre}\n` +
            `Contacto: ${contacto}\n` +
            `Empresa: ${empresa || '—'}\n` +
            `Solución solicitada: ${solucion}\n` +
            `Prefiere que le contacten por: ${preferencia || '—'}\n` +
            `Más información: ${info || '—'}\n`,
        }),
      });
    } catch (err) {
      // silencioso a propósito: la notificación es "nice to have", el dato ya está guardado
    }
  }

  return json({ ok: true });
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
