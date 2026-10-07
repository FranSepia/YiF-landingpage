"""
Regenera los archivos del sitio que dependen de las páginas:

    python _work/build.py

  - site/sitemap.xml   con <lastmod> real de cada página

Córrelo después de editar cualquier página de site/ y antes de hacer commit.
No necesita nada instalado aparte de Python 3 y git.
"""
import datetime
import os
import subprocess
from xml.sax.saxutils import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(RAIZ, 'site')
DOMINIO = 'https://www.why-and-if.solutions'

# Páginas indexables: (archivo dentro de site/, URL pública, changefreq, priority)
PAGINAS = [
    ('index.html', '/', 'monthly', '1.0'),
    ('soluciones.html', '/soluciones', 'monthly', '0.9'),
    ('why-innovation-atomic-model.html', '/why-innovation-atomic-model', 'monthly', '0.9'),
    ('ourwhy.html', '/ourwhy', 'monthly', '0.8'),
    ('contacto.html', '/contacto', 'monthly', '0.8'),
    ('tarjetas/y-and-if.html', '/tarjetas/y-and-if', 'yearly', '0.3'),
    ('tarjetas/humberto-gonzalez-olmos.html', '/tarjetas/humberto-gonzalez-olmos', 'yearly', '0.3'),
]


def git(*args):
    return subprocess.run(['git', *args], cwd=RAIZ, capture_output=True,
                          text=True, encoding='utf-8').stdout.strip()


def ultima_modificacion(archivo):
    """Fecha del último commit que tocó el archivo; hoy si tiene cambios sin
    commitear (lo normal al correr esto justo antes de hacer commit)."""
    ruta = 'site/' + archivo
    if git('status', '--porcelain', '--', ruta):
        return datetime.date.today().isoformat()
    fecha = git('log', '-1', '--format=%cs', '--', ruta)
    return fecha or datetime.date.today().isoformat()


def generar_sitemap():
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!-- Generado por _work/build.py: no lo edites a mano. -->',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for archivo, url, freq, prioridad in PAGINAS:
        lineas += [
            '  <url>',
            '    <loc>%s</loc>' % escape(DOMINIO + url),
            '    <lastmod>%s</lastmod>' % ultima_modificacion(archivo),
            '    <changefreq>%s</changefreq>' % freq,
            '    <priority>%s</priority>' % prioridad,
            '  </url>',
        ]
    lineas.append('</urlset>')
    with open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lineas) + '\n')
    print('sitemap.xml: %d URLs' % len(PAGINAS))


if __name__ == '__main__':
    generar_sitemap()
