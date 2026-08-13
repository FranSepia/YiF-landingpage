#!/usr/bin/env python3
"""
Reorganiza /site en carpetas por página.

  assets/shared/{css,fonts,js,img,docs}   assets que usan varias páginas
  assets/<pagina>/{img,video,js}          assets exclusivos de esa página
  assets/tarjetas/<tarjeta>/{img,video}   assets exclusivos de cada tarjeta
  tarjetas/<tarjeta>.html                 el HTML de cada tarjeta

Reglas fijas (no dependen del análisis de uso):
  · css/ y fonts/ SIEMPRE van juntos a shared/: los .css referencian
    ../fonts/... y romperlos costaría reescribir cada @font-face.
  · las librerías de terceros (jquery, splide, swiper, webflow) van a shared/js.

El resto se reparte por uso real: un asset citado por una sola página (o solo
por soluciones + soluciones-copy, que son la misma página) se va a esa carpeta;
si lo usan dos o más páginas distintas, se va a shared/.

Uso:  python _work/reorganize.py        (desde la raíz del proyecto)
"""

import json
import os
import re
import shutil
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

# página HTML -> carpeta de assets que le corresponde
PAGE_DIR = {
    "index.html": "home",
    "soluciones.html": "soluciones",
    "soluciones-copy.html": "soluciones",       # variante de la misma página
    "ourwhy.html": "ourwhy",
    "contacto.html": "contacto",
    "aliados-expertos.html": "aliados-expertos",
    "why-innovation-atomic-model.html": "why-innovation-atomic-model",
    "tarjeta-digital.html": "tarjetas/y-and-if",
    "tarjeta-digital-humberto-gonzalez-olmos.html": "tarjetas/humberto-gonzalez-olmos",
}

# HTML que se mueve a un subdirectorio: origen -> destino (relativo a site/)
PAGE_MOVE = {
    "tarjeta-digital.html": "tarjetas/y-and-if.html",
    "tarjeta-digital-humberto-gonzalez-olmos.html": "tarjetas/humberto-gonzalez-olmos.html",
}

VENDOR_JS = ("jquery", "splide", "swiper", "webflow")

TEXT_EXT = (".html", ".css", ".js", ".txt", ".json", ".xml", ".toml")


def rel(p):
    return p.replace("\\", "/")


def collect_assets():
    out = []
    for base, _, files in os.walk(os.path.join(SITE, "assets")):
        for fn in files:
            out.append(rel(os.path.relpath(os.path.join(base, fn), SITE)))
    return sorted(out)


def collect_textfiles():
    out = []
    for base, _, files in os.walk(SITE):
        for fn in files:
            if fn.endswith(TEXT_EXT):
                out.append(rel(os.path.relpath(os.path.join(base, fn), SITE)))
    return sorted(out)


def build_usage(assets, textfiles):
    """asset -> conjunto de páginas HTML que lo usan (directa o indirectamente)."""
    cited_by = collections.defaultdict(set)
    cache = {}
    for tf in textfiles:
        with open(os.path.join(SITE, tf), encoding="utf-8", errors="ignore") as fh:
            cache[tf] = fh.read()
    for a in assets:
        base = os.path.basename(a)
        for tf, body in cache.items():
            if tf != a and base in body:
                cited_by[a].add(tf)

    def pages_of(a, seen=None):
        seen = seen or set()
        pages = set()
        for citer in cited_by.get(a, ()):
            if citer.endswith(".html"):
                pages.add(citer)
            elif citer not in seen:
                seen.add(citer)
                pages |= pages_of(citer, seen)   # heredado del css/js que lo cita
        return pages

    return {a: pages_of(a) for a in assets}


def target_of(asset, pages):
    kind = asset.split("/")[1]          # css | fonts | js | img | video | docs
    name = os.path.basename(asset)

    if kind in ("css", "fonts"):
        return f"assets/shared/{kind}/{name}"
    if kind == "js" and any(v in name.lower() for v in VENDOR_JS):
        return f"assets/shared/js/{name}"

    dirs = {PAGE_DIR[p] for p in pages if p in PAGE_DIR}
    if len(dirs) == 1:
        return f"assets/{dirs.pop()}/{kind}/{name}"
    return f"assets/shared/{kind}/{name}"


def main():
    assets = collect_assets()
    textfiles = collect_textfiles()
    usage = build_usage(assets, textfiles)

    moves = {a: target_of(a, usage[a]) for a in assets}
    moves = {a: t for a, t in moves.items() if a != t}

    # 1) reescribe las referencias por texto, antes de tocar el disco.
    #    Se sustituye la ruta completa vieja por la nueva, así se respetan
    #    tanto las relativas ("assets/img/x.png") como las absolutas del
    #    dominio ("https://www.why-and-if.solutions/assets/img/x.png").
    for tf in textfiles:
        p = os.path.join(SITE, tf)
        with open(p, encoding="utf-8", errors="ignore") as fh:
            body = fh.read()
        orig = body
        for old, new in moves.items():
            if old in body:
                body = body.replace(old, new)
        if body != orig:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)

    # 2) mueve los archivos
    for old, new in sorted(moves.items()):
        src, dst = os.path.join(SITE, old), os.path.join(SITE, new)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)

    # 3) limpia los directorios viejos que quedaron vacíos
    for base, dirs, files in os.walk(os.path.join(SITE, "assets"), topdown=False):
        if not dirs and not files:
            os.rmdir(base)

    # 4) mueve el HTML de las tarjetas y ajusta sus rutas relativas.
    #    `assets/…` y `pagina.html` pasan a `../assets/…` y `../pagina.html`;
    #    el lookbehind evita tocar las URLs absolutas del dominio.
    for old, new in PAGE_MOVE.items():
        src, dst = os.path.join(SITE, old), os.path.join(SITE, new)
        with open(src, encoding="utf-8") as fh:
            body = fh.read()
        body = re.sub(r'(?<![/\w.-])assets/', '../assets/', body)
        body = re.sub(r'href="(?!http|#|/)([a-z0-9-]+\.html)"', r'href="../\1"', body)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.remove(src)

    report = {
        "assets_movidos": len(moves),
        "paginas_movidas": PAGE_MOVE,
        "por_carpeta": dict(collections.Counter(
            "/".join(t.split("/")[1:-1]) for t in moves.values())),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
