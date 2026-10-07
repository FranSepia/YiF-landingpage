"""
Regenera los archivos del sitio que dependen de las páginas:

    python _work/build.py

  - la versión en texto de las 6 órbitas en la página de Metodología
  - el JSON-LD (datos estructurados) de cada página, dentro de su <head>
  - la versión en inglés en site/en/ (a partir de los data-en de cada página),
    con hreflang y el botón ES/EN enlazando una con otra
  - ?v=<huella> en cada CSS/JS, para que un cambio se vea al publicarlo
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
    # La definición NO va aquí: se lee del párrafo .yf-home-intro de la home (oculto),
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

TEMAS_EN = [
    'Artificial intelligence', 'Process automation', 'Custom software development',
    'Digital transformation', 'Innovation management', 'Technology project management',
    'Digital product validation', 'Patents and intellectual property',
    'Market intelligence', 'Executive innovation training',
]

# Páginas indexables: archivo dentro de site/ → URL pública, tipo de página
# para schema.org, nombre corto (migas de pan) y datos del sitemap. Las que
# llevan 'en' tienen versión en inglés generada en site/en/ (ver más abajo).
PAGINAS = [
    {'archivo': 'index.html', 'url': '/', 'tipo': 'WebPage', 'miga': 'Inicio',
     'freq': 'monthly', 'prioridad': '1.0',
     'en': {'archivo': 'en/index.html', 'url': '/en/', 'miga': 'Home'}},
    {'archivo': 'soluciones.html', 'url': '/soluciones', 'tipo': 'CollectionPage',
     'miga': 'Soluciones', 'freq': 'monthly', 'prioridad': '0.9',
     'en': {'archivo': 'en/solutions.html', 'url': '/en/solutions', 'miga': 'Solutions'}},
    {'archivo': 'why-innovation-atomic-model.html', 'url': '/why-innovation-atomic-model',
     'tipo': 'WebPage', 'miga': 'Metodología WIAM', 'freq': 'monthly', 'prioridad': '0.9',
     'en': {'archivo': 'en/why-innovation-atomic-model.html', 'url': '/en/why-innovation-atomic-model',
            'miga': 'WIAM methodology'}},
    {'archivo': 'ourwhy.html', 'url': '/ourwhy', 'tipo': 'AboutPage',
     'miga': 'Lo que nos mueve', 'freq': 'monthly', 'prioridad': '0.8',
     'en': {'archivo': 'en/our-why.html', 'url': '/en/our-why', 'miga': 'What drives us'}},
    {'archivo': 'contacto.html', 'url': '/contacto', 'tipo': 'ContactPage',
     'miga': 'Contacto', 'freq': 'monthly', 'prioridad': '0.8',
     'en': {'archivo': 'en/contact.html', 'url': '/en/contact', 'miga': 'Contact'}},
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
    desc = re.search(r'<meta content="([^"]*)" name="description"', pagina_html)
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
    """La definición de Y&iF: el párrafo .yf-home-intro de la home (oculto a la
    vista con .yf-sr-only, pero en el HTML para buscadores y asistentes de IA)."""
    m = re.search(r'<p class="[^"]*\byf-home-intro\b[^"]*"' + ATTRS + r'>(.*?)</p>', leer('index.html'), re.S)
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
def zona(lang):
    if lang == 'en':
        return [{'@type': 'Country', 'name': 'Mexico'}, {'@type': 'Place', 'name': 'Latin America'}]
    return [{'@type': 'Country', 'name': 'México'}, {'@type': 'Place', 'name': 'Latinoamérica'}]


def organizacion(lang='es'):
    e = EMPRESA
    en = lang == 'en'
    org = {
        '@type': ['Organization', 'ProfessionalService'],
        '@id': ORG_ID,
        'name': e['nombre'],
        'alternateName': e['otros_nombres'],
        'url': DOMINIO + '/',
        'logo': {'@type': 'ImageObject', 'url': DOMINIO + e['logo'], 'width': 256, 'height': 256},
        'image': DOMINIO + e['imagen'],
        'description': definicion(lang),
        'slogan': e['eslogan'],
        'email': e['correo'],
        'telephone': e['telefono'],
        'address': e['direccion'],
        'hasMap': e['mapa'],
        'areaServed': zona(lang),
        'knowsAbout': TEMAS_EN if en else e['temas'],
        'knowsLanguage': ['es-MX', 'en'],
        'contactPoint': [
            {'@type': 'ContactPoint', 'contactType': 'sales', 'email': e['correo'],
             'telephone': e['telefono'], 'areaServed': 'MX',
             'availableLanguage': ['Spanish', 'English']},
            {'@type': 'ContactPoint', 'contactType': 'WhatsApp', 'telephone': e['whatsapp'],
             'availableLanguage': ['Spanish', 'English']},
        ],
        'hasOfferCatalog': {'@type': 'OfferCatalog',
                            'name': 'Y&iF solutions' if en else 'Soluciones de Y&iF',
                            'url': DOMINIO + ('/en/solutions' if en else '/soluciones')},
    }
    if e['perfiles']:
        org['sameAs'] = e['perfiles']
    return org


def sitio_web():
    return {'@type': 'WebSite', '@id': SITIO_ID, 'url': DOMINIO + '/', 'name': EMPRESA['nombre'],
            'alternateName': 'Why and If', 'inLanguage': ['es-MX', 'en'],
            'publisher': {'@id': ORG_ID}}


def migas(url, nombre, lang='es'):
    inicio = ('Home', DOMINIO + '/en/') if lang == 'en' else ('Inicio', DOMINIO + '/')
    return {'@type': 'BreadcrumbList', '@id': DOMINIO + url + '#migas', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': inicio[0], 'item': inicio[1]},
        {'@type': 'ListItem', 'position': 2, 'name': nombre, 'item': DOMINIO + url},
    ]}


def grafo(p, s=None, lang='es'):
    """JSON-LD de una página. `s` es su HTML (para la versión en inglés, que
    todavía no está escrita en disco cuando se arma)."""
    s = s if s is not None else leer(p['archivo'])
    en = lang == 'en'
    titulo, descripcion = meta(s)
    ruta = p['en']['url'] if en else p['url']
    url = DOMINIO + ruta
    pagina = {
        '@type': p['tipo'], '@id': url + '#pagina', 'url': url, 'name': titulo,
        'description': descripcion, 'inLanguage': 'en' if en else 'es-MX',
        'isPartOf': {'@id': SITIO_ID}, 'about': {'@id': ORG_ID},
    }
    nodos = [organizacion(lang), sitio_web(), pagina]
    if p['url'] != '/':
        pagina['breadcrumb'] = {'@id': url + '#migas'}
        nodos.append(migas(ruta, p['en']['miga'] if en else p['miga'], lang))

    if p['archivo'] == 'soluciones.html':
        nodos.append({
            '@type': 'ItemList', '@id': url + '#servicios',
            'name': 'Y&iF solutions' if en else 'Soluciones de Y&iF',
            'itemListElement': [
                {'@type': 'ListItem', 'position': i, 'item': {
                    '@type': 'Service', 'name': sv['nombre'],
                    'serviceType': sv['subtitulo_en'] if en else sv['subtitulo'],
                    'description': sv['texto_en'] if en else sv['texto'],
                    'provider': {'@id': ORG_ID}, 'areaServed': zona(lang), 'url': url}}
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


def con_jsonld(s, datos):
    nuevo = bloque_jsonld(datos)
    patron = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
    if patron.search(s):
        return patron.sub(lambda m: nuevo, s, count=1)
    return s.replace('</head>', nuevo + '</head>', 1)


def aplicar_jsonld():
    for p in PAGINAS:
        escribir(p['archivo'], con_jsonld(leer(p['archivo']), grafo(p)))
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
# Versión en inglés (site/en/) y enlaces entre idiomas
# --------------------------------------------------------------------------
# Cada página en español ya trae su traducción: data-en en los elementos (su
# contenido completo en inglés) y data-en-<atributo> en los atributos
# (data-en-content, data-en-alt, data-en-aria-label, data-en-value…). Antes un
# script cambiaba el texto en el navegador, así que Google sólo veía español;
# ahora site/en/ son páginas reales, con su URL, que los buscadores indexan.
# Se edita sólo la página en español y aquí se arma la inglesa.
ETIQUETA = re.compile(r'<(?P<cierre>/?)(?P<tag>[a-zA-Z][\w-]*)(?P<attrs>(?:\s+[\w:-]+(?:="[^"]*")?)*)\s*(?P<auto>/?)>')
MARCA_IDIOMAS = ('<!-- yf:idiomas -->', '<!-- /yf:idiomas -->')


def cierre_de(s, desde, tag):
    """(inicio, fin) del </tag> que cierra el elemento abierto justo antes de `desde`."""
    nivel = 1
    for m in ETIQUETA.finditer(s, desde):
        if m.group('tag').lower() != tag:
            continue
        if m.group('cierre'):
            nivel -= 1
        elif not m.group('auto'):
            nivel += 1
        if nivel == 0:
            return m.start(), m.end()
    raise ValueError('<%s> sin cierre' % tag)


def traducir(s):
    """Aplica data-en / data-en-<atributo> y los quita del HTML."""
    salida, pos = [], 0
    while True:
        m = ETIQUETA.search(s, pos)
        if not m:
            break
        tag = m.group('tag').lower()
        if not m.group('cierre') and tag in ('script', 'style'):
            fin = s.index('</%s>' % tag, m.end()) + len(tag) + 3
            salida.append(s[pos:fin])
            pos = fin
            continue
        if m.group('cierre') or 'data-en' not in m.group('attrs'):
            salida.append(s[pos:m.end()])
            pos = m.end()
            continue
        attrs = re.findall(r'\s+([\w:-]+)(?:="([^"]*)")?', m.group('attrs'))
        valores = dict(attrs)
        contenido = valores.get('data-en')
        nuevos = []
        for nombre, valor in attrs:
            if nombre == 'data-en' or nombre.startswith('data-en-'):
                continue
            if 'data-en-' + nombre in valores:
                valor = valores['data-en-' + nombre]
            nuevos.append((nombre, valor))
        # data-en-<x> sin atributo <x> en el original: se agrega.
        for nombre, valor in attrs:
            if nombre.startswith('data-en-') and nombre[8:] not in valores:
                nuevos.append((nombre[8:], valor))
        abre = '<%s%s%s>' % (m.group('tag'), ''.join(' %s="%s"' % (n, v) for n, v in nuevos),
                             '/' if m.group('auto') else '')
        if contenido is None:
            salida.append(s[pos:m.start()] + abre)
            pos = m.end()
            continue
        # El contenido se usa como lo haría innerHTML: se des-escapa el valor
        # del atributo y se vuelven a escapar los "&" sueltos (Y&iF).
        interior = re.sub(r'&(?![#\w]+;)', '&amp;', html.unescape(contenido))
        ini, fin = cierre_de(s, m.end(), tag)
        salida.append(s[pos:m.start()] + abre + interior + s[ini:fin])
        pos = fin
    salida.append(s[pos:])
    return ''.join(salida)


def boton_idioma(p, lang):
    """El botón ES/EN es un enlace a la misma página en el otro idioma."""
    if lang == 'es':
        return ('<a class="lang-toggle-btn" href="%s" hreflang="en" lang="en" title="English version">'
                'EN<span class="yf-sr-only"> — English version</span></a>' % p['en']['url'])
    return ('<a class="lang-toggle-btn" href="%s" hreflang="es-MX" lang="es-MX" title="Versión en español">'
            'ES<span class="yf-sr-only"> — versión en español</span></a>' % p['url'])


def con_idiomas(s, p, lang):
    """hreflang + og:locale:alternate en el <head> y el botón de idioma."""
    es, en = DOMINIO + p['url'], DOMINIO + p['en']['url']
    bloque = (MARCA_IDIOMAS[0] +
              '<link rel="alternate" hreflang="es-MX" href="%s"/>'
              '<link rel="alternate" hreflang="en" href="%s"/>'
              '<link rel="alternate" hreflang="x-default" href="%s"/>'
              '<meta property="og:locale:alternate" content="%s"/>' % (es, en, es, 'en_US' if lang == 'es' else 'es_MX') +
              MARCA_IDIOMAS[1])
    if MARCA_IDIOMAS[0] in s:
        s = re.sub(re.escape(MARCA_IDIOMAS[0]) + '.*?' + re.escape(MARCA_IDIOMAS[1]),
                   lambda m: bloque, s, count=1, flags=re.S)
    else:
        s = re.sub(r'(<link rel="canonical" href="[^"]*"/>)', lambda m: m.group(1) + bloque, s, count=1)
    boton = boton_idioma(p, lang)
    s, k = re.subn(r'<button type="button" class="lang-toggle-btn"[^>]*>EN</button>|'
                   r'<a class="lang-toggle-btn"[^>]*>.*?</a>', lambda m: boton, s, count=1, flags=re.S)
    assert k == 1, 'sin botón de idioma en ' + p['archivo']
    return s


def a_ingles(p):
    s = traducir(leer(p['archivo']))
    es, en = DOMINIO + p['url'], DOMINIO + p['en']['url']
    s = s.replace('<html lang="es-MX"', '<html lang="en"', 1)
    s = s.replace('<link rel="canonical" href="%s"/>' % es, '<link rel="canonical" href="%s"/>' % en)
    s = s.replace('<meta property="og:url" content="%s"/>' % es, '<meta property="og:url" content="%s"/>' % en)
    s = s.replace('<meta property="og:locale" content="es_MX"/>', '<meta property="og:locale" content="en_US"/>')
    titulo, descripcion = meta(s)
    t, d = html.escape(titulo, quote=True), html.escape(descripcion, quote=True)
    s = re.sub(r'<meta content="[^"]*" (property="og:title"|name="twitter:title")/>',
               lambda m: '<meta content="%s" %s/>' % (t, m.group(1)), s)
    s = re.sub(r'<meta content="[^"]*" (property="og:description"|name="twitter:description")/>',
               lambda m: '<meta content="%s" %s/>' % (d, m.group(1)), s)
    # La página vive un nivel abajo (/en/...): las rutas relativas suben uno.
    s = re.sub(r'(?<=[="\'(,;\s])assets/', '../assets/', s)
    # Los enlaces internos llevan a la versión en inglés.
    for q in PAGINAS:
        if 'en' in q:
            s = s.replace('href="%s"' % q['url'], 'href="%s"' % q['en']['url'])
    s = con_idiomas(s, p, 'en')
    if p['archivo'] == 'why-innovation-atomic-model.html':
        s = con_texto_wiam(s, 'en')
    return con_jsonld(s, grafo(p, s, 'en'))


def generar_ingles():
    n = 0
    for p in PAGINAS:
        if 'en' not in p:
            continue
        escribir(p['archivo'], con_idiomas(leer(p['archivo']), p, 'es'))
        escribir(p['en']['archivo'], a_ingles(p))
        n += 1
    print('Inglés: %d páginas en site/en/' % n)


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
          '- [English version](%s): the same site in English (/en/solutions, /en/contact…).' % url('/en/'),
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
# Versión en las URLs de CSS y JS
# --------------------------------------------------------------------------
# site/_headers deja CSS y JS una hora en la caché del navegador. Para que un
# cambio se vea en cuanto se publica, cada página los pide con ?v=<huella del
# contenido>: si el archivo cambia, cambia la URL y el navegador lo baja otra vez.
REF_ASSET = re.compile(r'((?:src|href)=")((?:\.\./|/)?assets/[^"?]+\.(?:css|js|txt))(?:\?v=[0-9a-f]+)?(")')


def versionar_assets():
    import glob
    import hashlib
    huellas = {}

    def huella(ruta):
        if ruta not in huellas:
            with open(ruta, 'rb') as f:
                # Sin CR: así la huella es la misma con finales de línea de Windows o de git.
                huellas[ruta] = hashlib.sha1(f.read().replace(b'\r\n', b'\n')).hexdigest()[:8]
        return huellas[ruta]

    n = 0
    for pagina in glob.glob(os.path.join(SITE, '**', '*.html'), recursive=True):
        if '.wrangler' in pagina:
            continue
        with open(pagina, encoding='utf-8') as f:
            s = f.read()

        def poner(m):
            ref = m.group(2)
            base = SITE if ref.startswith('/') else os.path.dirname(pagina)
            ruta = os.path.normpath(os.path.join(base, ref.lstrip('/')))
            if not os.path.isfile(ruta):
                return m.group(0)
            return '%s%s?v=%s%s' % (m.group(1), ref, huella(ruta), m.group(3))

        nuevo = REF_ASSET.sub(poner, s)
        if nuevo != s:
            with open(pagina, 'w', encoding='utf-8', newline='\n') as f:
                f.write(nuevo)
            n += 1
    print('CSS/JS versionados en %d páginas' % n)


# --------------------------------------------------------------------------
# sitemap.xml
# --------------------------------------------------------------------------
def generar_sitemap():
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!-- Generado por _work/build.py: no lo edites a mano. -->',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        ' xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    n = 0
    for p in PAGINAS:
        versiones = [(p['url'], p['archivo'])]
        if 'en' in p:
            versiones.append((p['en']['url'], p['en']['archivo']))
        for url, archivo in versiones:
            lineas += ['  <url>', '    <loc>%s</loc>' % escape(DOMINIO + url)]
            if 'en' in p:
                # Cada versión declara a las dos (y a la española como x-default).
                lineas += ['    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (h, escape(DOMINIO + u))
                           for h, u in (('es-MX', p['url']), ('en', p['en']['url']), ('x-default', p['url']))]
            lineas += [
                '    <lastmod>%s</lastmod>' % ultima_modificacion(archivo),
                '    <changefreq>%s</changefreq>' % p['freq'],
                '    <priority>%s</priority>' % p['prioridad'],
                '  </url>',
            ]
            n += 1
    lineas.append('</urlset>')
    escribir('sitemap.xml', '\n'.join(lineas) + '\n')
    print('sitemap.xml: %d URLs' % n)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # acentos en la consola de Windows
    except (AttributeError, ValueError):
        pass
    # El orden importa: la versión en inglés se arma a partir de las páginas
    # en español ya actualizadas, y el sitemap necesita las dos.
    aplicar_texto_wiam()
    aplicar_jsonld()
    generar_ingles()
    versionar_assets()
    generar_llms()
    generar_sitemap()
