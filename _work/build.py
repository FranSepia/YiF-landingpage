"""
Regenera los archivos del sitio que dependen de las páginas:

    python _work/build.py

  - la versión en texto de las 6 órbitas en la página de Metodología
  - el JSON-LD (datos estructurados) de cada página, dentro de su <head>
  - site/llms.txt y site/llms-full.txt (resumen y contenido completo para IA)
  - site/sitemap.xml   con <lastmod> real de cada página

Córrelo después de editar cualquier página de site/ y antes de hacer commit.
No necesita nada instalado aparte de Python 3 y git.

Los datos de la empresa (nombre, dirección, teléfonos, descripción) viven en
EMPRESA, más abajo: es la única fuente. Así el JSON-LD dice exactamente lo
mismo en todas las páginas, que es lo que buscadores y asistentes de IA usan
para reconocer a Y&iF como una sola entidad. Los títulos, descripciones y
textos de las soluciones se leen del propio HTML.
"""
import datetime
import html
import json
import os
import re
import subprocess
import sys
from xml.sax.saxutils import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(RAIZ, 'site')
DOMINIO = 'https://www.why-and-if.solutions'
ORG_ID = DOMINIO + '/#organizacion'
SITIO_ID = DOMINIO + '/#sitio'

# --------------------------------------------------------------------------
# Datos de la empresa. Si cambia algo (teléfono, dirección, redes), cámbialo
# aquí y corre el script: se actualiza en todo el sitio.
# --------------------------------------------------------------------------
EMPRESA = {
    'nombre': 'Y&iF',
    'otros_nombres': ['Why and If', 'Y&F Group'],
    'eslogan': 'Purpose Driven Tech',
    # La definición NO va aquí: se lee del párrafo .yf-home-intro de la home,
    # para que lo que dice la página y lo que dice el JSON-LD sea lo mismo.
    'sectores': 'sector público, corporativo y empresas, sector educativo, y tecnología y startups',
    'correo': 'contacto@why-and-if.solutions',
    'telefono': '+52-55-4748-0723',
    'whatsapp': '+52-55-7009-9790',
    'direccion': {
        '@type': 'PostalAddress',
        'streetAddress': 'Monte Elbruz 124, Piso 2, Int. 212-B, Lomas de Chapultepec III Secc.',
        'addressLocality': 'Miguel Hidalgo',
        'addressRegion': 'Ciudad de México',
        'postalCode': '11000',
        'addressCountry': 'MX',
    },
    'mapa': 'https://maps.app.goo.gl/zqt2GMcJAYJtLnjb9',
    'logo': '/assets/shared/img/6902b31ad7c600dab5f20254_Logo-estudio-creativo-logo-negro-corculo-blanco-256x256.png',
    'imagen': '/assets/shared/img/6902ae9dffdd293241d2c0fe_logo-para-comartir.jpg',
    # Perfiles oficiales (LinkedIn de la empresa, Instagram, Google Business…).
    # Vacío a propósito hasta tener las URLs reales: sameAs es de lo que más
    # pesa para que los buscadores unan el sitio con esos perfiles.
    'perfiles': [],
    'temas': [
        'Inteligencia artificial', 'Automatización de procesos',
        'Desarrollo de software a la medida', 'Transformación digital',
        'Gestión de la innovación', 'Dirección de proyectos tecnológicos',
        'Validación de productos digitales', 'Patentes y propiedad intelectual',
        'Inteligencia de mercado', 'Formación ejecutiva en innovación',
    ],
}

# Páginas indexables: archivo dentro de site/ → URL pública, tipo de página
# para schema.org, nombre corto (migas de pan) y datos del sitemap.
PAGINAS = [
    {'archivo': 'index.html', 'url': '/', 'tipo': 'WebPage', 'miga': 'Inicio',
     'freq': 'monthly', 'prioridad': '1.0'},
    {'archivo': 'soluciones.html', 'url': '/soluciones', 'tipo': 'CollectionPage',
     'miga': 'Soluciones', 'freq': 'monthly', 'prioridad': '0.9'},
    {'archivo': 'why-innovation-atomic-model.html', 'url': '/why-innovation-atomic-model',
     'tipo': 'WebPage', 'miga': 'Metodología WIAM', 'freq': 'monthly', 'prioridad': '0.9'},
    {'archivo': 'ourwhy.html', 'url': '/ourwhy', 'tipo': 'AboutPage',
     'miga': 'Lo que nos mueve', 'freq': 'monthly', 'prioridad': '0.8'},
    {'archivo': 'contacto.html', 'url': '/contacto', 'tipo': 'ContactPage',
     'miga': 'Contacto', 'freq': 'monthly', 'prioridad': '0.8'},
    {'archivo': 'tarjetas/y-and-if.html', 'url': '/tarjetas/y-and-if', 'tipo': 'WebPage',
     'miga': 'Tarjeta digital', 'freq': 'yearly', 'prioridad': '0.3'},
    {'archivo': 'tarjetas/humberto-gonzalez-olmos.html', 'url': '/tarjetas/humberto-gonzalez-olmos',
     'tipo': 'ProfilePage', 'miga': 'Humberto González Olmos', 'freq': 'yearly', 'prioridad': '0.3',
     'persona': {'nombre': 'Humberto González Olmos', 'descripcion': (
         'Profesional con +30 años en alta dirección internacional en la industria del '
         'juego. Apasionado por convertir retos complejos en resultados medibles, con '
         'visión estratégica, liderazgo ejecutivo y enfoque en crecimiento y expansión.')}},
]


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def leer(ruta):
    with open(os.path.join(SITE, ruta), encoding='utf-8') as f:
        return f.read()


def escribir(ruta, contenido):
    destino = os.path.join(SITE, ruta)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, 'w', encoding='utf-8', newline='\n') as f:
        f.write(contenido)


def texto(fragmento):
    """HTML → texto plano de una línea."""
    fragmento = re.sub(r'<br\s*/?>', ' ', fragmento)
    fragmento = html.unescape(re.sub(r'<[^>]+>', '', fragmento))
    return re.sub(r'\s+', ' ', fragmento.replace('‍', '')).strip()


def meta(pagina_html):
    """(título, descripción) tal como están en el <head>."""
    titulo = re.search(r'<title[^>]*>(.*?)</title>', pagina_html, re.S)
    desc = re.search(r'<meta content="([^"]*)" name="description"/>', pagina_html)
    return (texto(titulo.group(1)) if titulo else '',
            html.unescape(desc.group(1)) if desc else '')


def git(*args):
    return subprocess.run(['git', *args], cwd=RAIZ, capture_output=True,
                          text=True, encoding='utf-8').stdout.strip()


def ultima_modificacion(archivo):
    """Fecha del último commit que tocó el archivo; hoy si tiene cambios sin
    commitear (lo normal al correr esto justo antes de hacer commit)."""
    ruta = 'site/' + archivo
    if git('status', '--porcelain', '--', ruta):
        return datetime.date.today().isoformat()
    return git('log', '-1', '--format=%cs', '--', ruta) or datetime.date.today().isoformat()


def texto_md(fragmento):
    """HTML → Markdown sencillo: respeta los saltos y convierte las viñetas •."""
    fragmento = re.sub(r'<br\s*/?>', '\n', fragmento)
    fragmento = re.sub(r'</?strong>', '**', fragmento)
    fragmento = html.unescape(re.sub(r'<[^>]+>', '', fragmento)).replace('‍', '')
    lineas = [re.sub(r'\s+', ' ', l).strip() for l in fragmento.split('\n')]
    lineas = ['- ' + l[1:].strip() if l.startswith('•') else l for l in lineas if l]
    return '\n'.join(lineas)


ATTRS = r'((?:\s+[\w:-]+(?:="[^"]*")?)*)'  # atributos completos (data-en lleva "<br/>")


def data_en(attrs):
    m = re.search(r'data-en="([^"]*)"', attrs)
    return html.unescape(m.group(1)) if m else ''


# --------------------------------------------------------------------------
# Contenido que se lee del HTML
# --------------------------------------------------------------------------
def definicion(lang='es'):
    """La definición de Y&iF: el párrafo bajo el logo de la home."""
    m = re.search(r'<p class="yf-home-intro"' + ATTRS + r'>(.*?)</p>', leer('index.html'), re.S)
    return texto(data_en(m.group(1)) if lang == 'en' else m.group(2))


def literal_js(fuente, nombre):
    """Lee `const NOMBRE=[...]` de un <script> y lo devuelve como dato de
    Python. Las claves de JS van sin comillas: se recorre el texto saltando
    las cadenas para no tocar lo que va dentro de ellas."""
    inicio = fuente.index('[', fuente.index(nombre + '='))
    salida, i, nivel = [], inicio, 0
    while True:
        c = fuente[i]
        if c in '"\'':
            j = i + 1
            while fuente[j] != c:
                j += 2 if fuente[j] == '\\' else 1
            cadena = fuente[i + 1:j].replace("\\'", "'")  # \' es válido en JS, no en JSON
            if c == "'":
                cadena = cadena.replace('"', '\\"')
            salida.append('"' + cadena + '"')
            i = j + 1
            continue
        clave = re.match(r'[A-Za-z_$][\w$]*(?=\s*:)', fuente[i:])
        if clave:
            salida.append('"%s"' % clave.group(0))
            i += clave.end()
            continue
        nivel += c in '[{'
        nivel -= c in ']}'
        salida.append(c)
        i += 1
        if nivel == 0:
            break
    return json.loads(re.sub(r',(\s*[\]}])', r'\1', ''.join(salida)))


def orbitas(lang='es'):
    """Las 6 órbitas del WIAM tal como las usa el diagrama interactivo."""
    fuente = leer('why-innovation-atomic-model.html')
    return literal_js(fuente, 'ORBITS_EN' if lang == 'en' else 'ORBITS_ES')


def tarjetas_de_texto(archivo, lang='es'):
    """Tarjetas de "Lo que nos mueve" y de los pilares de la Metodología:
    lista de (título, texto en Markdown)."""
    s = leer(archivo)
    salida = []
    titulos = list(re.finditer(r'<h[23] class="benefits_card_titlef?"' + ATTRS + r'>(.*?)</h[23]>', s, re.S))
    for n, t in enumerate(titulos):
        fin = titulos[n + 1].start() if n + 1 < len(titulos) else len(s)
        parrafos = re.findall(r'<p class="benefits_card_textf?[^"]*"' + ATTRS + r'>(.*?)</p>', s[t.end():fin], re.S)
        if lang == 'en':
            cuerpo = '\n\n'.join(texto_md(data_en(a)) for a, _ in parrafos if data_en(a))
            titulo = texto(data_en(t.group(1))) or texto(t.group(2))
        else:
            cuerpo = '\n\n'.join(texto_md(c) for _, c in parrafos)
            titulo = texto(t.group(2))
        salida.append((titulo, cuerpo))
    return salida


def servicios():
    """Las 11 soluciones de site/soluciones.html: nombre, subtítulo, texto."""
    s = leer('soluciones.html')
    salida = []
    # Los atributos se recorren completos porque data-en lleva "<br/>" adentro.
    attrs = r'((?:\s+[\w:-]+(?:="[^"]*")?)*)'
    for bloque in re.findall(r'<div class="swiper-slide">(.*?)</div></div></div></div></div>', s, re.S):
        nombre = re.search(r'<h2' + attrs + r'>(.*?)</h2>', bloque, re.S)
        sub = re.search(r'<h3' + attrs + r'>(.*?)</h3>', bloque, re.S)
        cuerpo = re.search(r'<div class="text-md[^"]*"' + attrs + r'>(.*)', bloque, re.S)
        if not (nombre and sub and cuerpo):
            continue
        en = lambda m: re.search(r'data-en="([^"]*)"', m.group(1))
        salida.append({
            'nombre': texto(nombre.group(2)),
            'subtitulo': texto(sub.group(2)),
            'texto': texto(cuerpo.group(2)),
            'subtitulo_en': texto(html.unescape(en(sub).group(1))) if en(sub) else '',
            'texto_en': texto(html.unescape(en(cuerpo).group(1))) if en(cuerpo) else '',
        })
    return salida


# --------------------------------------------------------------------------
# JSON-LD
# --------------------------------------------------------------------------
def organizacion():
    e = EMPRESA
    org = {
        '@type': ['Organization', 'ProfessionalService'],
        '@id': ORG_ID,
        'name': e['nombre'],
        'alternateName': e['otros_nombres'],
        'url': DOMINIO + '/',
        'logo': {'@type': 'ImageObject', 'url': DOMINIO + e['logo'], 'width': 256, 'height': 256},
        'image': DOMINIO + e['imagen'],
        'description': definicion(),
        'slogan': e['eslogan'],
        'email': e['correo'],
        'telephone': e['telefono'],
        'address': e['direccion'],
        'hasMap': e['mapa'],
        'areaServed': [{'@type': 'Country', 'name': 'México'},
                       {'@type': 'Place', 'name': 'Latinoamérica'}],
        'knowsAbout': e['temas'],
        'knowsLanguage': ['es-MX', 'en'],
        'contactPoint': [
            {'@type': 'ContactPoint', 'contactType': 'sales', 'email': e['correo'],
             'telephone': e['telefono'], 'areaServed': 'MX',
             'availableLanguage': ['Spanish', 'English']},
            {'@type': 'ContactPoint', 'contactType': 'WhatsApp', 'telephone': e['whatsapp'],
             'availableLanguage': ['Spanish', 'English']},
        ],
        'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': 'Soluciones de Y&iF',
                            'url': DOMINIO + '/soluciones'},
    }
    if e['perfiles']:
        org['sameAs'] = e['perfiles']
    return org


def sitio_web():
    return {'@type': 'WebSite', '@id': SITIO_ID, 'url': DOMINIO + '/', 'name': EMPRESA['nombre'],
            'alternateName': 'Why and If', 'inLanguage': 'es-MX',
            'publisher': {'@id': ORG_ID}}


def migas(url, nombre):
    return {'@type': 'BreadcrumbList', '@id': DOMINIO + url + '#migas', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Inicio', 'item': DOMINIO + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': nombre, 'item': DOMINIO + url},
    ]}


def grafo(p):
    s = leer(p['archivo'])
    titulo, descripcion = meta(s)
    url = DOMINIO + p['url']
    pagina = {
        '@type': p['tipo'], '@id': url + '#pagina', 'url': url, 'name': titulo,
        'description': descripcion, 'inLanguage': 'es-MX',
        'isPartOf': {'@id': SITIO_ID}, 'about': {'@id': ORG_ID},
    }
    nodos = [organizacion(), sitio_web(), pagina]
    if p['url'] != '/':
        pagina['breadcrumb'] = {'@id': url + '#migas'}
        nodos.append(migas(p['url'], p['miga']))

    if p['archivo'] == 'soluciones.html':
        nodos.append({
            '@type': 'ItemList', '@id': url + '#servicios', 'name': 'Soluciones de Y&iF',
            'itemListElement': [
                {'@type': 'ListItem', 'position': i, 'item': {
                    '@type': 'Service', 'name': sv['nombre'], 'serviceType': sv['subtitulo'],
                    'description': sv['texto'], 'provider': {'@id': ORG_ID},
                    'areaServed': [{'@type': 'Country', 'name': 'México'},
                                   {'@type': 'Place', 'name': 'Latinoamérica'}],
                    'url': url}}
                for i, sv in enumerate(servicios(), 1)],
        })
        pagina['mainEntity'] = {'@id': url + '#servicios'}

    if p['tipo'] == 'ProfilePage':
        linkedin = re.search(r'href="(https://www\.linkedin\.com/in/[^"]+)"', s)
        foto = re.search(r'<meta content="([^"]+)" property="og:image"/>', s)
        persona = {'@type': 'Person', 'name': p['persona']['nombre'],
                   'description': p['persona']['descripcion']}
        if foto:
            persona['image'] = foto.group(1)
        if linkedin:
            persona['sameAs'] = [linkedin.group(1)]
        pagina['mainEntity'] = persona

    return {'@context': 'https://schema.org', '@graph': nodos}


def bloque_jsonld(datos):
    cuerpo = json.dumps(datos, ensure_ascii=False, separators=(',', ':'))
    return '<script type="application/ld+json">%s</script>' % cuerpo.replace('</', '<\\/')


def aplicar_jsonld():
    for p in PAGINAS:
        s = leer(p['archivo'])
        nuevo = bloque_jsonld(grafo(p))
        patron = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
        if patron.search(s):
            s = patron.sub(lambda m: nuevo, s, count=1)
        else:
            s = s.replace('</head>', nuevo + '</head>', 1)
        escribir(p['archivo'], s)
    print('JSON-LD: %d páginas' % len(PAGINAS))


# --------------------------------------------------------------------------
# Metodología: versión en texto del diagrama
# --------------------------------------------------------------------------
# El contenido de las órbitas (definición, preguntas clave, herramientas) sólo
# existe dentro del <script> del diagrama, y los crawlers de IA normalmente no
# ejecutan JavaScript. Esta sección lo deja en el HTML, oculta a la vista con
# .yf-sr-only (la misma información ya se ve al tocar cada órbita) pero
# legible para lectores de pantalla, Google y asistentes de IA.
MARCA_WIAM = ('<!-- yf:wiam-texto (generado por _work/build.py) -->', '<!-- /yf:wiam-texto -->')
TEXTOS_WIAM = {
    'es': {'titulo': 'Las seis órbitas del modelo WIAM',
           'intro': 'Versión en texto del diagrama interactivo del Why Innovation Atomic Model.',
           'preguntas': 'Preguntas clave', 'herramientas': 'Herramientas'},
    'en': {'titulo': 'The six orbits of the WIAM model',
           'intro': 'Text version of the interactive Why Innovation Atomic Model diagram.',
           'preguntas': 'Key questions', 'herramientas': 'Tools'},
}


def html_wiam(lang='es'):
    t = TEXTOS_WIAM[lang]
    e = lambda x: html.escape(x, quote=False)
    partes = ['<section class="yf-sr-only" id="wiam-texto" aria-labelledby="wiam-texto-titulo">',
              '<h2 id="wiam-texto-titulo">%s</h2><p>%s</p>' % (e(t['titulo']), e(t['intro']))]
    for o in orbitas(lang):
        partes.append('<h3>%s: %s</h3><p>%s</p>' % (e(o['name']), e(o['subtitle']), e(o['definition'])))
        partes.append('<h4>%s</h4><ul>%s</ul>' % (e(t['preguntas']), ''.join('<li>%s</li>' % e(q) for q in o['questions'])))
        partes.append('<h4>%s</h4><ul>%s</ul>' % (e(t['herramientas']), ''.join('<li>%s</li>' % e(h) for h in o['tools'])))
    partes.append('</section>')
    return MARCA_WIAM[0] + ''.join(partes) + MARCA_WIAM[1]


def con_texto_wiam(s, lang='es'):
    bloque = html_wiam(lang)
    if MARCA_WIAM[0] in s:
        return re.sub(re.escape(MARCA_WIAM[0]) + '.*?' + re.escape(MARCA_WIAM[1]),
                      lambda m: bloque, s, count=1, flags=re.S)
    ancla = '<div role="list" class="benefits_layoutf">'
    assert ancla in s, 'no encontré dónde poner el texto del WIAM'
    return s.replace(ancla, bloque + ancla, 1)


def aplicar_texto_wiam():
    archivo = 'why-innovation-atomic-model.html'
    escribir(archivo, con_texto_wiam(leer(archivo)))
    print('Metodología: texto de %d órbitas' % len(orbitas()))


# --------------------------------------------------------------------------
# llms.txt y llms-full.txt (https://llmstxt.org)
# --------------------------------------------------------------------------
def generar_llms():
    hoy = datetime.date.today().isoformat()
    e = EMPRESA
    d = e['direccion']
    direccion = '%s, %s, C.P. %s, %s, México' % (d['streetAddress'], d['addressLocality'],
                                                 d['postalCode'], d['addressRegion'])
    sv = servicios()
    orb = orbitas()
    url = lambda u: DOMINIO + u

    # --- llms.txt: resumen con enlaces -----------------------------------
    l = ['# Y&iF (Why and If)', '', '> ' + definicion(), '',
         'Y&iF opera bajo el lema "%s": tecnología con propósito y resultados medibles. '
         'Trabaja con %s.' % (e['eslogan'], e['sectores']), '',
         'Datos clave:', '',
         '- Sede: Ciudad de México (Miguel Hidalgo), México',
         '- Mercado: México y Latinoamérica',
         '- Idiomas: español e inglés',
         '- Soluciones: %d (lista abajo)' % len(sv),
         '- Metodología propia: Why Innovation Atomic Model (WIAM), de seis órbitas',
         '', '## Soluciones', '']
    for s_ in sv:
        l.append('- [%s](%s): %s. %s' % (s_['nombre'], url('/soluciones'), s_['subtitulo'], s_['texto']))
    l += ['', '## Metodología', '',
          '- [Why Innovation Atomic Model (WIAM)](%s): modelo propio de Y&iF que organiza la '
          'innovación en seis órbitas alrededor de un núcleo de objetivos estratégicos: %s.'
          % (url('/why-innovation-atomic-model'),
             '; '.join('%s (%s)' % (o['name'], o['subtitle'].lower()) for o in orb)),
          '', '## Páginas', '',
          '- [Inicio](%s): quiénes somos, en una frase.' % url('/'),
          '- [Lo que nos mueve](%s): misión, visión y propósito.' % url('/ourwhy'),
          '- [Soluciones](%s): las %d soluciones, con su descripción.' % (url('/soluciones'), len(sv)),
          '- [Metodología WIAM](%s): las seis órbitas, con preguntas clave y herramientas.' % url('/why-innovation-atomic-model'),
          '- [Contacto](%s): formulario para iniciar una conversación.' % url('/contacto'),
          '', '## Contacto', '',
          '- Correo: ' + e['correo'],
          '- Teléfono: ' + e['telefono'].replace('-', ' '),
          '- WhatsApp: ' + e['whatsapp'].replace('-', ' '),
          '- Dirección: ' + direccion,
          '', '## Optional', '',
          '- [Contenido completo en Markdown](%s): todo el texto del sitio en un solo archivo.' % url('/llms-full.txt'),
          '- [Tarjeta digital de Y&iF](%s): datos de contacto en formato tarjeta.' % url('/tarjetas/y-and-if'),
          '']
    escribir('llms.txt', '\n'.join(l))

    # --- llms-full.txt: todo el contenido ---------------------------------
    f = ['# Y&iF (Why and If) — contenido completo del sitio', '',
         '> ' + definicion(), '',
         'Fuente: %s · Actualizado: %s · Generado a partir de las páginas publicadas.' % (url('/'), hoy), '',
         '## Quiénes somos', '',
         '- Nombre: %s (también %s)' % (e['nombre'], ', '.join(e['otros_nombres'])),
         '- Lema: ' + e['eslogan'],
         '- Sede: ' + direccion,
         '- Mercado: México y Latinoamérica',
         '- Sectores: ' + e['sectores'],
         '- Idiomas: español e inglés',
         '', '## Lo que nos mueve', '', 'Página: ' + url('/ourwhy'), '']
    for titulo, cuerpo in tarjetas_de_texto('ourwhy.html'):
        f += ['### ' + titulo, '', cuerpo, '']
    f += ['## Soluciones', '', 'Página: ' + url('/soluciones'), '']
    for s_ in sv:
        f += ['### %s — %s' % (s_['nombre'], s_['subtitulo']), '', s_['texto'], '']
    f += ['## Metodología: Why Innovation Atomic Model (WIAM)', '',
          'Página: ' + url('/why-innovation-atomic-model'), '']
    for titulo, cuerpo in tarjetas_de_texto('why-innovation-atomic-model.html'):
        f += ['### ' + titulo, '', cuerpo, '']
    f += ['### Las seis órbitas', '']
    for o in orb:
        f += ['#### %s — %s' % (o['name'], o['subtitle']), '', o['definition'], '',
              'Preguntas clave:', ''] + ['- ' + q for q in o['questions']] + \
             ['', 'Herramientas: ' + ', '.join(o['tools']) + '.', '']
    f += ['## Contacto', '',
          '- Formulario: ' + url('/contacto'),
          '- Correo: ' + e['correo'],
          '- Teléfono: ' + e['telefono'].replace('-', ' '),
          '- WhatsApp: ' + e['whatsapp'].replace('-', ' '),
          '- Dirección: ' + direccion, '']
    escribir('llms-full.txt', '\n'.join(f))
    print('llms.txt y llms-full.txt: %d soluciones, %d órbitas' % (len(sv), len(orb)))


# --------------------------------------------------------------------------
# sitemap.xml
# --------------------------------------------------------------------------
def generar_sitemap():
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!-- Generado por _work/build.py: no lo edites a mano. -->',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in PAGINAS:
        lineas += [
            '  <url>',
            '    <loc>%s</loc>' % escape(DOMINIO + p['url']),
            '    <lastmod>%s</lastmod>' % ultima_modificacion(p['archivo']),
            '    <changefreq>%s</changefreq>' % p['freq'],
            '    <priority>%s</priority>' % p['prioridad'],
            '  </url>',
        ]
    lineas.append('</urlset>')
    escribir('sitemap.xml', '\n'.join(lineas) + '\n')
    print('sitemap.xml: %d URLs' % len(PAGINAS))


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # acentos en la consola de Windows
    except (AttributeError, ValueError):
        pass
    aplicar_texto_wiam()
    aplicar_jsonld()
    generar_llms()
    generar_sitemap()
