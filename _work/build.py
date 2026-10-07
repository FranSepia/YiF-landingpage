"""
Regenera los archivos del sitio que dependen de las páginas:

    python _work/build.py

  - el JSON-LD (datos estructurados) de cada página, dentro de su <head>
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
    'definicion': (
        'Y&iF (Why and If) es una consultoría de innovación tecnológica e '
        'inteligencia artificial con sede en la Ciudad de México que ayuda a '
        'empresas, gobierno y sector educativo de México y LATAM a diseñar, '
        'validar y construir soluciones digitales —automatización con IA, '
        'software a la medida y transformación digital— con su metodología '
        'propia, WIAM.'
    ),
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


# --------------------------------------------------------------------------
# Contenido que se lee del HTML
# --------------------------------------------------------------------------
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
        'description': e['definicion'],
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
    aplicar_jsonld()
    generar_sitemap()
