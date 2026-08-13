# Duplicado Landing Page Y&iF — copia estática

Copia estática y auto-contenida del sitio **https://www.why-and-if.solutions/** (originalmente en Webflow, plan gratuito), lista para desplegar en **Cloudflare Pages** (con el formulario de contacto funcionando vía Pages Functions + D1) o, sin el formulario, en Vercel/Netlify — sin depender de Webflow ni de ningún CDN externo.

Fecha de clonado: **2026-08-12** · Último publicado del original: *Tue May 19 2026*.

---

## 📁 Estructura

```
Duplicado Landing Page Y&iF/
├── site/                     ← ESTO es lo que se despliega (raíz del sitio)
│   ├── index.html            ← home (/)
│   ├── contacto.html         ← /contacto
│   ├── ourwhy.html           ← /ourwhy
│   ├── soluciones.html       ← /soluciones
│   ├── soluciones-copy.html  ← /soluciones-copy
│   ├── why-innovation-atomic-model.html
│   ├── aliados-expertos.html
│   ├── tarjetas/             ← todas las tarjetas digitales viven aquí
│   │   ├── y-and-if.html                 ← /tarjetas/y-and-if
│   │   └── humberto-gonzalez-olmos.html  ← /tarjetas/humberto-gonzalez-olmos
│   ├── assets/               ← organizados POR PÁGINA
│   │   ├── shared/           ← lo que usan varias páginas
│   │   │   ├── css/   (8)  hojas de estilo
│   │   │   ├── fonts/ (20) woff2 de Montserrat (variable) y Bitter
│   │   │   ├── js/    (7)  Webflow, jQuery, Splide, Swiper
│   │   │   ├── img/   (21) logos, favicons, OG, badge, iconos comunes
│   │   │   └── docs/  (1)  Aviso de Privacidad (PDF)
│   │   ├── home/             ← solo index.html      (4 img + watercolor-home.js)
│   │   ├── soluciones/       ← soluciones + soluciones-copy (32 img + 1 js)
│   │   ├── ourwhy/           ← solo ourwhy.html     (3 img + 6 video)
│   │   ├── why-innovation-atomic-model/             (1 img)
│   │   └── tarjetas/         ← una carpeta por tarjeta
│   │       ├── y-and-if/                 (3 img + 2 video)
│   │       └── humberto-gonzalez-olmos/  (16 img + 2 video)
│   │   └── contacto/js/      ← contact-form.js (envía el form a /api/contact)
│   ├── functions/
│   │   └── api/contact.js    ← Cloudflare Pages Function: guarda el lead en D1 + avisa por correo
│   ├── favicon.ico
│   ├── robots.txt
│   ├── sitemap.xml
│   ├── vercel.json           ← URLs limpias + redirects de las tarjetas
│   └── netlify.toml
├── _work/                    ← material de trabajo (NO se despliega)
│   ├── localize.py           ← baja el sitio original y genera /site (plano)
│   ├── reorganize.py         ← reparte /site/assets en carpetas por página
│   ├── serve_nocache.py      ← servidor local sin caché
│   ├── d1/schema.sql         ← esquema de la tabla `leads` (formulario de contacto)
│   ├── _raw/                 ← HTML original descargado de cada página
│   └── _watercolor_script.txt← script del efecto de acuarela (referencia)
├── LICENSE                    ← propiedad de Y&F Group, no es open source
├── THIRD-PARTY-NOTICES.md     ← avisos MIT/OFL de las librerías incluidas
└── README.md
```

Todo lo que se sirve al público está dentro de **`site/`**. La carpeta `_work/` es solo para regenerar o auditar la copia.

### Dónde va un asset nuevo

- Lo usa **una sola página** → `assets/<esa-página>/<tipo>/`
- Lo usan **dos o más** → `assets/shared/<tipo>/`
- Es de **una tarjeta** → `assets/tarjetas/<nombre-de-la-tarjeta>/<tipo>/`

> **`css/` y `fonts/` se quedan siempre en `shared/`**, aunque solo los use una
> página: los `.css` referencian las fuentes con rutas relativas (`../fonts/…`)
> y separarlos obligaría a reescribir cada `@font-face`.

`contacto` y `aliados-expertos` no tienen carpeta propia: todo lo que usan es
compartido. Una página solo estrena carpeta cuando tiene algún archivo suyo.

### Añadir una tarjeta nueva

1. Copia `site/tarjetas/y-and-if.html` a `site/tarjetas/<nombre>.html`.
2. Crea `site/assets/tarjetas/<nombre>/img/` (y `video/` si hace falta) con sus archivos.
3. Dentro del HTML las rutas van con `../` porque el archivo está un nivel abajo:
   `../assets/tarjetas/<nombre>/img/foto.jpg`, `../assets/shared/css/…`.
4. Agrégala al `sitemap.xml`. Queda publicada en `https://tu-dominio/tarjetas/<nombre>`.

---

## ▶️ Correr en local

```bash
python _work/serve_nocache.py      # http://127.0.0.1:8124/
```

Este es el recomendado: manda cabeceras `no-cache`, así ves los cambios sin
tener que forzar recarga. Alternativa, desde la carpeta `site/`:

```bash
python -m http.server 8123
```

Abre **http://127.0.0.1:8123/**. (Cualquier servidor estático sirve: `npx serve`, etc.)

> Ábrelo con un servidor, **no** con doble-clic (`file://`), porque las fuentes, el
> WebGL y algunas rutas relativas no cargan bien bajo `file://`.

---

## 🚀 Desplegar

En los tres casos, **la carpeta a publicar es `site/`** (no la raíz del proyecto).

| Plataforma | Cómo |
|---|---|
| **Cloudflare Pages** (la que se usa hoy) | Conecta el repo de GitHub, *build output directory* = `site`. Trae **URLs limpias** por defecto y sirve `site/functions/api/contact.js` automáticamente (la función del formulario de contacto). Ver el paso a paso completo en la sección del formulario, más abajo. |
| **Vercel** | Arrastra `site/` en vercel.com/new, o `cd site && vercel`. El `vercel.json` ya activa URLs limpias. El formulario de contacto **no funciona aquí tal cual** — está escrito como Cloudflare Pages Function + D1; en Vercel habría que reescribirlo como Vercel Function + otra base de datos. |
| **Netlify** | Arrastra `site/` en app.netlify.com/drop, o conecta el repo con *publish directory* = `site`. Netlify sirve `/contacto` desde `contacto.html` automáticamente. Mismo caso: el formulario necesitaría reescribirse como Netlify Function. |

Después apunta tu dominio **why-and-if.solutions** al nuevo host (registro DNS) y listo.

---

## ✅ Qué quedó 100 % idéntico

- **Las 9 páginas** del `sitemap.xml` (incluidas las no enlazadas desde el menú: `soluciones-copy`, `aliados-expertos`, ambas tarjetas digitales).
- **Favicon** (32×32) y **apple-touch-icon** (256×256), auto-hospedados.
- **Open Graph / Twitter Card** (`og:title`, `og:description`, `og:image`, `twitter:card`…) con la **imagen de preview descargada** y servida localmente. La `og:image` se dejó como **URL absoluta** (`https://www.why-and-if.solutions/assets/shared/img/…`) porque WhatsApp/redes exigen URL absoluta para el preview.
- **Efecto de acuarela con el cursor**: es la *WebGL Fluid Simulation* de Pavel Dobryakov (MIT), un script WebGL autocontenido (sin p5/Three/GSAP). Descargado y servido en local; verificado que inicializa contexto **WebGL2** y corre.
- **Animaciones/interacciones de Webflow** (líneas de los botones, etc.), **carruseles Splide y Swiper**, y **videos de fondo** (mp4 + webm + poster) — todos cargan y reproducen en local.
- **Fuentes auto-hospedadas**: Montserrat (fuente *variable*, todos los pesos + itálicas) y Bitter, en `assets/shared/fonts/` — **cero llamadas a Google Fonts**.
- **0 dependencias externas de assets**: no se contacta a `website-files.com`, `googleapis`, `gstatic`, `jsdelivr` ni `cloudfront`. Se conservan solo los **enlaces salientes legítimos** (WhatsApp, LinkedIn, Google Maps, el aliado *lahuellaviva.com*).

---

## 🔁 Qué requirió sustitución o atención

### 1. Formulario de contacto (`contacto.html`) — resuelto, corre en Cloudflare Pages

El formulario `email-form` enviaba a los servidores de **Webflow**, que ya no existen. Se reemplazó por una **Cloudflare Pages Function** propia: `site/functions/api/contact.js`, que guarda cada envío en **D1** (la base SQL de Cloudflare) y opcionalmente avisa por correo vía **Resend**. Cero servicios de terceros que cobren, cero límite de envíos/mes.

Cómo quedó armado (para que sepas qué tocar si algo cambia):

- El wrapper del formulario dejó de tener la clase `w-form` (ahora es `yif-form`) — así el runtime de Webflow ya no intenta interceptar el submit y mandarlo a `webflow.com`, que es lo que causaba el "Oops! Something went wrong" cuando lo probaste antes.
- `site/assets/contacto/js/contact-form.js` intercepta el submit, arma un `FormData` y hace `fetch` a `/api/contact`. Muestra el mismo mensaje de éxito/error que ya traía el diseño (`.w-form-done` / `.w-form-fail`), no se ve nada distinto.
- Lleva un campo trampa para bots (`name="website"`, oculto con CSS). Si un bot lo rellena, se le responde "éxito" sin guardar nada — spam invisible, sin CAPTCHA.
- Si JavaScript está desactivado, el `<form method="post" action="/api/contact">` igual funciona (Cloudflare sabe leer tanto `multipart/form-data` como el POST nativo del navegador), aunque sin el mensaje dinámico.

**Para activarlo en tu cuenta de Cloudflare, antes del primer deploy:**

1. **Crea la base D1** (una nueva, dedicada a este sitio — no mezcles con la de tu otro proyecto):
   ```bash
   npx wrangler login
   npx wrangler d1 create yif-landingpage-leads
   ```
   Te va a imprimir un `database_id`; guárdalo, lo pides en el paso 3.

2. **Aplica el esquema** (crea la tabla `leads`):
   ```bash
   npx wrangler d1 execute yif-landingpage-leads --remote --file=_work/d1/schema.sql
   ```

3. **Conecta el repo en Cloudflare Pages** (dashboard → Workers & Pages → Create → Pages → conecta `FranSepia/YiF-landingpage`):
   - *Build output directory*: `site`
   - *Build command*: (vacío, es HTML estático)
   - En **Settings → Functions → D1 database bindings**: variable `DB` → tu base `yif-landingpage-leads`.

4. **(Opcional pero recomendado) Aviso por correo con Resend:**
   - Crea una cuenta gratis en https://resend.com y copia tu API key (100 correos/día gratis).
   - En **Settings → Environment variables**, agrega `RESEND_API_KEY` como **Secret**.
   - Sin verificar tu dominio en Resend, el correo sale desde `onboarding@resend.dev` — funciona perfecto porque es solo un aviso interno para ustedes, no algo que vea el cliente. Si más adelante quieres que salga de `@why-and-if.solutions`, verificas el dominio en Resend y cambias la variable opcional `NOTIFY_FROM`.
   - Si no configuras `RESEND_API_KEY`, el formulario sigue funcionando igual — el lead se guarda en D1, simplemente no llega el correo.

**Cómo revisar los leads que van llegando:**
```bash
npx wrangler d1 execute yif-landingpage-leads --remote --command "SELECT * FROM leads ORDER BY created_at DESC"
```
O desde el dashboard: Workers & Pages → D1 → `yif-landingpage-leads` → pestaña *Tables*.

**Probarlo en tu máquina antes de subir cambios** (sin tocar tu cuenta real de Cloudflare, usa una base D1 local de prueba):
```bash
cd site
npx wrangler pages dev . --d1 DB=test-local
```
Abre `http://127.0.0.1:8788/contacto`, llena el formulario y mándalo. Para darle datos a esa base local, corre el mismo `wrangler d1 execute ... --local --file=...` sin `--remote`.

Mientras tanto, el contacto sigue disponible también por los datos del pie: **contacto@why-and-if.solutions**, **55 4748 0723** y los botones de **WhatsApp**.

### 2. Badge "Made in Webflow" — **opcional**
El original (plan gratuito) inyecta el badge "Made in Webflow" abajo a la derecha. Para mantener la copia idéntica y sin dependencias, se **descargaron sus 2 SVG** y se parchó el JS para servirlos localmente. Como ya no usas Webflow, **puedes quitarlo**: en `assets/shared/js/webflow.schunk.46f2c06d4a0bdbdb.js` está el código que lo crea (busca `w-webflow-badge`), o simplemente añade en tu CSS `.w-webflow-badge{display:none!important}`.

### 3. Dominio de la `og:image`
Las `og:image` apuntan a `https://www.why-and-if.solutions/...`. Si despliegas primero en un dominio temporal (`*.vercel.app`), el preview social seguirá pidiendo la imagen a tu dominio final. Cuando el dominio propio ya apunte al nuevo host, funciona sin tocar nada. Si prefieres otro dominio definitivo, reemplaza esa base en los `<meta property="og:image">` (o vuelve a correr `_work/localize.py` cambiando `SITE_BASE`).

---

## 🎨 Personalizaciones respecto al original

- **Home: efecto de acuarela reactivo al *hover*.** En el sitio original, en la home el efecto solo se pintaba al **hacer clic**; en las demás pantallas se pinta al **pasar el cursor**. Se unificó: ahora la home también reacciona al mover el cursor (sin clic), igual que el resto. El cambio vive en `assets/home/js/watercolor-home.js` (copia dedicada del script con el `mousemove` habilitado para hover) y `index.html` la referencia. No afecta a `soluciones`/`soluciones-copy`, que conservan su propio script. El clic sigue funcionando igual.

- **Soluciones: carrusel ajustado.** (1) La **tarjeta central** (activa) se muestra un poco más grande — factor ajustable en el `<style id="yif-custom">` de `soluciones.html`, variable `--yif-active-scale` (1.16 = +16 %). (2) Al hacer **clic en una tarjeta lateral**, el carrusel se **centra en ella** (opción `slideToClickedSlide: true` de Swiper). Ambos cambios están en `soluciones.html`.

### Páginas sin enlace en el menú (cómo verlas)
Estas páginas existen pero no tienen botón en la navegación (igual que en el original). Se abren por URL directa:

| Página | En local | Desplegada |
|---|---|---|
| Tarjeta digital (empresa, Y&iF) | `http://127.0.0.1:8123/tarjetas/y-and-if.html` | `https://tu-dominio/tarjetas/y-and-if` |
| Tarjeta digital — Humberto | `http://127.0.0.1:8123/tarjetas/humberto-gonzalez-olmos.html` | `https://tu-dominio/tarjetas/humberto-gonzalez-olmos` |
| Soluciones (copia) | `http://127.0.0.1:8123/soluciones-copy.html` | `https://tu-dominio/soluciones-copy` |
| Aliados expertos | `http://127.0.0.1:8123/aliados-expertos.html` | `https://tu-dominio/aliados-expertos` |

Si quieres que alguna sea accesible con un botón/enlace (en el menú, el pie, o desde otra página), se puede agregar.

## ⚠️ Notas de fidelidad (comportamiento idéntico al original)

- **`GET /LDR_LLL1_0.png → 404` en consola**: es la textura de *dithering* que el script de acuarela intenta cargar. **El sitio original también da 404** en ese archivo, así que el efecto se ve exactamente igual (el sim corre sin esa textura). No es un error de la copia.
- **`[splide] null is invalid` en la home**: la home ejecuta el init de Splide aunque no tiene carrusel. **El original hace lo mismo**; es inofensivo.
- **CMS dinámico**: no se detectaron *Collection Lists* con contenido paginado/dinámico. Las páginas se capturaron como **snapshot estático** del HTML publicado, por lo que cualquier contenido que en Webflow fuera de CMS queda "congelado" (no se actualiza solo). Si en el futuro necesitas contenido editable, habría que montar un CMS aparte.

---

## 🧩 Regenerar la copia

Todo `site/` se reconstruye de forma reproducible con **dos pasos, en este orden**:

```bash
python _work/localize.py     # 1. baja el original -> site/ con assets planos
python _work/reorganize.py   # 2. reparte los assets en carpetas por página
```

`localize.py` descarga el HTML de las 9 rutas, baja y localiza todos los assets (CSS/JS/imágenes/videos/fuentes/PDF), auto-hospeda las fuentes de Google, reescribe los enlaces internos a rutas locales y deja `og:image` absoluta. Variables ajustables al inicio del script: `PAGES`, `SITE_BASE`.

> ⚠️ **`localize.py` genera la estructura plana vieja** (`assets/img/`, `assets/js/`…)
> y deja las tarjetas en la raíz. Si lo corres solo, deshace la organización por
> carpetas. **Siempre corre `reorganize.py` después.** `reorganize.py` decide a
> qué carpeta va cada archivo analizando qué páginas lo citan de verdad, así que
> funciona aunque el sitio original cambie de assets.

---

## ❌ Assets que no se pudieron recuperar

Ninguno. Los **128 assets** referenciados por las páginas se descargaron correctamente (0 fallos, 0 archivos corruptos), y las **452 referencias locales** del HTML resuelven a archivos existentes. Los únicos recursos que "faltan" son los que **tampoco existían en el original** (la textura `LDR_LLL1_0.png`, ver arriba).

---

## ⚖️ Licencias de terceros

### Efecto de acuarela / fluido — **WebGL Fluid Simulation**

El efecto que pinta el canvas al pasar el cursor es
[WebGL-Fluid-Simulation](https://github.com/PavelDoGreat/WebGL-Fluid-Simulation)
de **Pavel Dobryakov**, publicado bajo **licencia MIT**.

La MIT permite usarlo, modificarlo y venderlo en un sitio comercial sin pagar
nada — con **una única condición**: que el aviso de copyright y el texto de la
licencia viajen con cada copia del código. Por eso el bloque `/* MIT License …
Copyright (c) 2017 Pavel Dobryakov … */` está al inicio de **cada copia** del
script:

| Dónde | Cómo |
|---|---|
| `index.html` | lo carga externo desde `assets/home/js/watercolor-home.js` (el aviso va en ese archivo) |
| `soluciones.html`, `soluciones-copy.html` | `assets/soluciones/js/613b…_script.txt` + copia inline |
| las otras 8 páginas | copia **inline** dentro del `<script>` del fondo de fluido |

> **No borres esos comentarios.** Son lo único que hace legal el uso del efecto;
> si un minificador los quita, configúralo para preservar los comentarios de
> licencia (en Terser/esbuild es la opción `legal-comments`). Tampoco hace falta
> ponerlo en la página visible: basta con que esté en el código, que es lo que
> pide la MIT.

### Otras librerías incluidas

| Librería | Licencia | Ubicación |
|---|---|---|
| jQuery 3.5.1 | MIT | `assets/shared/js/` |
| Splide | MIT | `assets/shared/js/`, `assets/shared/css/` |
| Swiper | MIT | `assets/shared/js/`, `assets/shared/css/` |
| Montserrat, Bitter | SIL Open Font License 1.1 | `assets/shared/fonts/` |
| Runtime de Webflow | del sitio original, ya pagado/exportado | `assets/shared/js/` |
