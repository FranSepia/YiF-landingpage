#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Localizador del sitio Webflow why-and-if.solutions -> copia estatica.
Lee _raw/*.html, descarga todos los assets, auto-hospeda las fuentes,
reescribe todos los enlaces a rutas locales relativas y escribe en ../site.
"""
import os, re, sys, subprocess, hashlib, urllib.parse, json

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(ROOT, "_raw")
SITE = os.path.abspath(os.path.join(ROOT, "..", "site"))
ASSETS = os.path.join(SITE, "assets")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

PAGES = {
    "index": "/",
    "contacto": "/contacto",
    "ourwhy": "/ourwhy",
    "soluciones": "/soluciones",
    "why-innovation-atomic-model": "/why-innovation-atomic-model",
    "tarjeta-digital": "/tarjeta-digital",
    "aliados-expertos": "/aliados-expertos",
    "tarjeta-digital-humberto-gonzalez-olmos": "/tarjeta-digital-humberto-gonzalez-olmos",
    "soluciones-copy": "/soluciones-copy",
}
# path (sin barra inicial) -> archivo local
PATH2FILE = {}
for name, p in PAGES.items():
    key = "" if p == "/" else p.strip("/")
    PATH2FILE[key] = name + ".html"

SITE_HOST = "www.why-and-if.solutions"
# Dominio final de despliegue: og:image/twitter:image DEBEN ser absolutas para
# que WhatsApp/redes muestren el preview. Cambiar si se despliega a otro dominio.
SITE_BASE = "https://www.why-and-if.solutions"
LOCALIZE_PREFIXES = (
    "https://cdn.prod.website-files.com/",
    "https://d3e54v103j8qbb.cloudfront.net/",
    "https://cdn.jsdelivr.net/",
    "https://fonts.gstatic.com/",
)

for d in ("css", "js", "img", "video", "fonts", "docs"):
    os.makedirs(os.path.join(ASSETS, d), exist_ok=True)

# --- descarga con curl (TLS robusto en Windows) ---
def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-sL", "--fail", "-A", UA, "-o", dest, url],
                       capture_output=True)
    ok = r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0
    if not ok:
        print("  !! FALLO:", url)
        if os.path.exists(dest) and os.path.getsize(dest) == 0:
            os.remove(dest)
    return ok

def fetch_text(url):
    r = subprocess.run(["curl", "-sL", "--fail", "-A", UA, url], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")

# --- clasificar y nombrar assets ---
EXT_DIR = {
    ".css": "css", ".js": "js", ".txt": "js",
    ".woff2": "fonts", ".woff": "fonts", ".ttf": "fonts", ".otf": "fonts", ".eot": "fonts",
    ".mp4": "video", ".webm": "video", ".ogg": "video", ".mov": "video",
    ".pdf": "docs", ".svg": "img",
    ".png": "img", ".jpg": "img", ".jpeg": "img", ".gif": "img", ".webp": "img", ".avif": "img", ".ico": "img",
}

def sanitize(name):
    name = urllib.parse.unquote(name)
    name = name.replace("&", "and").replace(" ", "-")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = re.sub(r"_+", "_", name).strip("._-") or "asset"
    return name

url_map = {}       # url original (tal cual en el HTML/CSS) -> ruta local relativa a la raiz del site
_used_names = {}   # dir -> set de nombres usados

def local_for(url):
    """Devuelve la ruta local (relativa a la raiz del site) para una URL a localizar."""
    if url in url_map:
        return url_map[url]
    # normalizar: quitar query, decodificar %2F para partir el path
    clean = url.split("?")[0].split("#")[0]
    clean = clean.replace("%2F", "/").replace("%2f", "/")
    base = clean.rsplit("/", 1)[-1]
    root, ext = os.path.splitext(base)
    ext = ext.lower()
    sub = EXT_DIR.get(ext, "img")
    fname = sanitize(base)
    if not os.path.splitext(fname)[1]:
        fname += ext
    # unicidad por carpeta
    used = _used_names.setdefault(sub, {})
    if fname in used and used[fname] != url:
        h = hashlib.md5(url.encode()).hexdigest()[:6]
        r2, e2 = os.path.splitext(fname)
        fname = f"{r2}-{h}{e2}"
    used[fname] = url
    rel = f"assets/{sub}/{fname}"
    url_map[url] = rel
    return rel

# --- extraer URLs a localizar de un texto HTML ---
def is_localizable(u):
    return u.startswith(LOCALIZE_PREFIXES)

def find_asset_urls(html):
    urls = set()
    # href/src en atributos con comillas dobles y simples
    for m in re.finditer(r'(?:href|src|content|poster)\s*=\s*"([^"]+)"', html):
        urls.add(m.group(1))
    for m in re.finditer(r"(?:href|src|content|poster)\s*=\s*'([^']+)'", html):
        urls.add(m.group(1))
    # srcset (separado por comas; cada item "url  descriptor")
    for m in re.finditer(r'srcset\s*=\s*"([^"]+)"', html):
        for part in m.group(1).split(","):
            u = part.strip().split()[0] if part.strip() else ""
            if u:
                urls.add(u)
    # url(...) dentro de estilos inline, con &quot; o comillas o sin ellas
    for m in re.finditer(r'url\((?:&quot;|["\'])?(https?://[^)"\'&]+)(?:&quot;|["\'])?\)', html):
        urls.add(m.group(1))
    return {u for u in urls if is_localizable(u)}

# --- reescritor comun de url() en CSS (respeta comillas y \escape) ---
CSS_URL_RE = re.compile(
    r'''url\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|((?:[^)\\\s]|\\.)*))\s*\)''')

def _css_unescape(s):
    return re.sub(r'\\(.)', r'\1', s)

def rewrite_css_urls(txt, base_url, dest_path):
    def repl(m):
        raw = m.group(1) or m.group(2) or m.group(3) or ""
        raw = _css_unescape(raw.strip())
        if raw == "" or raw.startswith("data:") or raw.startswith("#"):
            return m.group(0)                       # fragmentos SVG y data: intactos
        abs_url = urllib.parse.urljoin(base_url, raw)
        abs_url = re.sub(r'\s+', '', abs_url)
        if not (is_localizable(abs_url) or abs_url.startswith("https://fonts.gstatic.com")):
            return m.group(0)
        rel = local_for(abs_url)
        download(abs_url, os.path.join(SITE, rel))
        rel_from_css = os.path.relpath(os.path.join(SITE, rel),
                                       os.path.dirname(dest_path)).replace("\\", "/")
        return f"url({rel_from_css})"
    return CSS_URL_RE.sub(repl, txt)

# --- procesar CSS: descargar y localizar sus url() recursivamente ---
processed_css = set()
def process_css_file(css_url, dest_path):
    txt = fetch_text(css_url)
    if txt is None:
        print("  !! No pude bajar CSS:", css_url)
        return
    txt = rewrite_css_urls(txt, css_url, dest_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(txt)

# --- fuentes de Google (auto-hospedaje) ---
def build_google_css(url, out_name):
    """Baja una hoja de Google Fonts con UA de navegador y localiza sus woff2."""
    dest = os.path.join(ASSETS, "css", out_name)
    txt = fetch_text(url)
    if txt is None:
        print("  !! No pude bajar Google CSS:", url); return None
    txt = rewrite_css_urls(txt, url, dest)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(txt)
    return "assets/css/" + out_name

def main():
    # 1) hoja de fuentes equivalente al WebFont.load (Montserrat todos los pesos + Bitter)
    weights = ",".join(f"{w},{w}italic" for w in range(100, 1000, 100))
    webfont_url = ("https://fonts.googleapis.com/css?family="
                   "Montserrat:" + weights + "|Bitter:400,700,400italic&display=swap")
    print("Fuentes: Montserrat + Bitter (webfonts.css) ...")
    webfonts_css = build_google_css(webfont_url, "webfonts.css")

    # 2) procesar cada pagina
    for name, path in PAGES.items():
        src = os.path.join(RAW, name + ".html")
        html = open(src, encoding="utf-8").read()
        print(f"\nPagina: {name}")

        # 2a) localizar assets (css/js/img/video/fonts/docs)
        for u in sorted(find_asset_urls(html), key=len, reverse=True):
            u_clean = re.sub(r'\s+', '', u)          # quita saltos de linea internos
            rel = local_for(u_clean)
            full = os.path.join(SITE, rel)
            if rel.startswith("assets/css/") and u_clean.endswith(".css"):
                if u_clean not in processed_css:
                    processed_css.add(u_clean)
                    print("  css:", u_clean.rsplit('/',1)[-1])
                    process_css_file(u_clean, full)
            else:
                download(u_clean, full)
            html = html.replace(u, rel)

        # 2b) Google Fonts css2 <link> -> hoja local
        def css2_repl(m):
            gurl = m.group(1).replace("&amp;", "&")
            key = "gf_" + hashlib.md5(gurl.encode()).hexdigest()[:8] + ".css"
            if ("assets/css/" + key) not in url_map.values():
                print("  google css2:", gurl)
                build_google_css(gurl, key)
            return m.group(0).replace(m.group(1), "assets/css/" + key)
        # reemplazo directo de los <link ... href="https://fonts.googleapis.com/css2...">
        def link_css2(m):
            full_tag = m.group(0)
            href = m.group(1)
            gurl = href.replace("&amp;", "&")
            key = "gf_" + hashlib.md5(gurl.encode()).hexdigest()[:8] + ".css"
            local_css = build_google_css(gurl, key)
            print("  google css2:", gurl)
            newtag = re.sub(r'href\s*=\s*"[^"]*"', f'href="{local_css}"', full_tag)
            newtag = newtag.replace(" crossorigin", "").replace(' integrity=""', "")
            return newtag
        html = re.sub(r'<link[^>]*href="(https://fonts\.googleapis\.com/css2[^"]*)"[^>]*>',
                      link_css2, html)

        # 2b2) @import url('.../css2...') dentro de <style> inline -> hoja local
        def import_css2(m):
            quote = m.group(1)
            gurl = m.group(2).replace("&amp;", "&")
            key = "gf_" + hashlib.md5(gurl.encode()).hexdigest()[:8] + ".css"
            if not os.path.exists(os.path.join(ASSETS, "css", key)):
                print("  google @import:", gurl)
                build_google_css(gurl, key)
            return f"@import url({quote}assets/css/{key}{quote})"
        html = re.sub(
            r"@import\s+url\((['\"]?)(https://fonts\.googleapis\.com/css2[^'\")]+)\1\)",
            import_css2, html)

        # 2b3) quitar preconnect/dns-prefetch a hosts externos ya localizados
        html = re.sub(
            r'<link[^>]*rel="(?:preconnect|dns-prefetch)"[^>]*'
            r'(?:fonts\.googleapis\.com|fonts\.gstatic\.com|cdn\.prod\.website-files\.com)[^>]*/?>',
            '', html)
        html = re.sub(
            r'<link[^>]*(?:fonts\.googleapis\.com|fonts\.gstatic\.com|cdn\.prod\.website-files\.com)[^>]*'
            r'rel="(?:preconnect|dns-prefetch)"[^>]*/?>',
            '', html)

        # 2c) reemplazar webfont.js + WebFont.load por <link> local
        if webfonts_css:
            html = re.sub(r'<script[^>]*ajax\.googleapis\.com/ajax/libs/webfont[^>]*></script>',
                          f'<link rel="stylesheet" href="{webfonts_css}"/>', html)
            html = re.sub(r'<script type="text/javascript">WebFont\.load\(.*?\}\);</script>',
                          '', html, flags=re.DOTALL)

        # 2d) enlaces internos absolutos del propio dominio -> archivo local
        def internal_abs(m):
            p = m.group(2).strip("/").split("?")[0].split("#")[0]
            frag = m.group(2)[len(m.group(2).rstrip()):]  # no-op
            if p in PATH2FILE:
                tail = m.group(2)[len("/" + p):] if m.group(2).startswith("/" + p) else ""
                return f'{m.group(1)}="{PATH2FILE[p]}{tail}"'
            if p == "" :
                return f'{m.group(1)}="index.html"'
            return m.group(0)
        html = re.sub(r'(href|src)\s*=\s*"https?://www\.why-and-if\.solutions(/[^"]*)?"',
                      lambda m: f'{m.group(1)}="{rewrite_internal(m.group(2) or "/")}"', html)

        # 2e) enlaces root-relative /ruta -> archivo local
        html = re.sub(r'href\s*=\s*"(/[^":#?]*)((?:[#?][^"]*)?)"',
                      lambda m: f'href="{rewrite_internal(m.group(1))}{m.group(2)}"', html)

        # 2f) quitar integrity de recursos ya locales (SRI romperia si el byte difiere)
        html = re.sub(r'\s+integrity="[^"]*"', "", html)
        # crossorigin en recursos locales es inocuo; lo dejamos salvo en <link>/<script> locales
        html = re.sub(r'(<(?:script|link)[^>]*(?:assets/)[^>]*?)\s+crossorigin="[^"]*"',
                      r'\1', html)

        # 2g) og:image / twitter:image -> URL ABSOLUTA (crawlers sociales lo exigen)
        def abs_social(m):
            return m.group(0).replace('content="assets/', f'content="{SITE_BASE}/assets/')
        html = re.sub(r'<meta[^>]*content="assets/[^"]+"[^>]*(?:og:image|twitter:image)[^>]*>',
                      abs_social, html)
        html = re.sub(r'<meta[^>]*(?:og:image|twitter:image)[^>]*content="assets/[^"]+"[^>]*>',
                      abs_social, html)

        out = os.path.join(SITE, name + ".html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("  -> escrito", name + ".html")

    # 3) localizar el badge "Made in Webflow" referenciado dentro del JS de Webflow
    badge = {
        "https://d3e54v103j8qbb.cloudfront.net/img/webflow-badge-icon-d2.89e12c322e.svg":
            "assets/img/webflow-badge-icon-d2.89e12c322e.svg",
        "https://d3e54v103j8qbb.cloudfront.net/img/webflow-badge-text-d2.c82cec3b78.svg":
            "assets/img/webflow-badge-text-d2.c82cec3b78.svg",
    }
    for url, rel in badge.items():
        download(url, os.path.join(SITE, rel))
    for jsf in os.listdir(os.path.join(ASSETS, "js")):
        p = os.path.join(ASSETS, "js", jsf)
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        new = txt
        for url, rel in badge.items():
            new = new.replace(url, rel)
        if new != txt:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new)
            print("  badge localizado en", jsf)

    # 3b) CUSTOMIZACION Y&iF: efecto de acuarela en la HOME reactivo al HOVER
    #     (el original solo reacciona al clic). Se crea una copia dedicada del
    #     script y se repunta index.html, sin afectar soluciones/soluciones-copy.
    wc_src = os.path.join(ASSETS, "js", "613b6a6361dc95d04258d19b_script.txt")
    wc_dst = os.path.join(ASSETS, "js", "watercolor-home.js")
    if os.path.exists(wc_src):
        s = open(wc_src, encoding="utf-8").read()
        old = ("    if (!pointer.down) { return; }\n"
               "    var posX = scaleByPixelRatio(e.offsetX);\n"
               "    var posY = scaleByPixelRatio(e.offsetY);\n"
               "    updatePointerMoveData(pointer, posX, posY);")
        new = ("    var posX = scaleByPixelRatio(e.offsetX);\n"
               "    var posY = scaleByPixelRatio(e.offsetY);\n"
               "    // Y&iF: reaccionar al hover (sin necesidad de clic), como en las demas pantallas\n"
               "    if (!pointer.down) { updatePointerDownData(pointer, -1, posX, posY); }\n"
               "    updatePointerMoveData(pointer, posX, posY);")
        if old in s:
            open(wc_dst, "w", encoding="utf-8").write(s.replace(old, new, 1))
            idx = os.path.join(SITE, "index.html")
            ih = open(idx, encoding="utf-8").read()
            ih = ih.replace("assets/js/613b6a6361dc95d04258d19b_script.txt",
                            "assets/js/watercolor-home.js")
            open(idx, "w", encoding="utf-8").write(ih)
            print("  home: efecto de acuarela reactivo al hover (watercolor-home.js)")
        else:
            print("  !! no se encontro el bloque de mousemove para el patch de hover")

    # 3c) CUSTOMIZACION Y&iF (soluciones):
    #     - todas las tarjetas al mismo tamano (mas grandes) via JS; la central
    #       se destaca por la perspectiva 3D de Swiper -> sin "salto" al centrarse
    #     - la tarjeta agrandada no se recorta (overflow) y se eleva un poco
    #     - clic en una tarjeta lateral -> la centra (atraviesa las zonas .area-*)
    #     - anti-parpadeo: el carrusel se revela cuando ya tiene el tamano final
    sol = os.path.join(SITE, "soluciones.html")
    if os.path.exists(sol):
        sh = open(sol, encoding="utf-8").read()
        changed = False
        if "slideToClickedSlide" not in sh and "grabCursor: true," in sh:
            sh = sh.replace("grabCursor: true,",
                            "grabCursor: true,\n\t\tslideToClickedSlide: true,", 1)
            changed = True
        style_anchor = '</head><body class="body-8"><section class="page_wrap_seccion soluciones">'
        style = '''<style id="yif-custom">
/* Y&iF: la tarjeta central completa se agranda por JS (ver #yif-swiper-extra) */
/* Permitir que la tarjeta agrandada sobresalga arriba/abajo SIN recortarse,
   manteniendo el recorte horizontal (para no desparramar el resto del loop). */
.swiper{ overflow: visible !important; }
.swiper-component{ overflow-x: clip !important; overflow-y: visible !important; }
/* Anti-parpadeo: ocultar las tarjetas hasta que el JS fije el tamano final */
.swiper .swiper-wrapper{ opacity: 0; }
.swiper.yif-ready .swiper-wrapper{ opacity: 1; transition: opacity .18s ease; }
</style>'''
        if "yif-custom" not in sh and style_anchor in sh:
            sh = sh.replace(style_anchor, style + style_anchor, 1)
            changed = True
        script = r'''<script id="yif-swiper-extra">
/* Y&iF: (1) agranda TODAS las tarjetas por igual (sin "salto" al centrarse)
         (2) clic en cualquier tarjeta lateral -> la centra (atraviesa zonas .area-*)
         (3) anti-parpadeo: revela el carrusel cuando ya tiene el tamano final */
(function(){
  var SCALE = 1.20;   /* factor de tamano de las tarjetas: sube/baja aqui */
  var LIFT  = 48;     /* cuanto se eleva la tarjeta (px) para no tapar el texto de abajo */
  function start(){
    var el = document.querySelector('.swiper');
    var sw = el && el.swiper;
    if(!sw){ return setTimeout(start, 200); }
    function applyScale(){
      var slides = el.querySelectorAll('.swiper-slide');
      for(var i=0;i<slides.length;i++){
        var s = slides[i];
        var t = (s.style.transform || '').replace(/\s*(translateY|scale)\([^)]*\)/g,'');
        s.style.transformOrigin = 'center center';
        s.style.transform = t + ' translateY(-' + LIFT + 'px) scale(' + SCALE + ')';
      }
    }
    sw.on('setTranslate', applyScale);
    sw.on('slideChange', applyScale);
    sw.on('slideChangeTransitionEnd', applyScale);
    sw.on('transitionEnd', applyScale);
    sw.on('resize', applyScale);
    applyScale();
    el.classList.add('yif-ready');
    document.addEventListener('click', function(e){
      var stack = document.elementsFromPoint(e.clientX, e.clientY) || [];
      var slide = null;
      for(var i=0;i<stack.length;i++){
        if(stack[i].classList && stack[i].classList.contains('swiper-slide')){ slide = stack[i]; break; }
      }
      if(!slide || slide.classList.contains('swiper-slide-active')) return;
      var idx = slide.getAttribute('data-swiper-slide-index');
      if(idx === null) return;
      if(typeof sw.slideToLoop === 'function') sw.slideToLoop(parseInt(idx,10));
      else sw.slideTo(parseInt(idx,10));
    }, true);
  }
  setTimeout(function(){ var el=document.querySelector('.swiper'); if(el) el.classList.add('yif-ready'); }, 1500);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
</script>'''
        if "yif-swiper-extra" not in sh and "</body></html>" in sh:
            sh = sh.replace("</body></html>", script + "\n</body></html>", 1)
            changed = True
        if changed:
            open(sol, "w", encoding="utf-8").write(sh)
            print("  soluciones: tarjetas uniformes mas grandes + clic-para-centrar + anti-parpadeo")

    # 4) sitemap y robots locales
    print("\nAssets unicos descargados:", len(url_map))
    # guardar mapa para depurar
    with open(os.path.join(ROOT, "_urlmap.json"), "w", encoding="utf-8") as f:
        json.dump(url_map, f, indent=1, ensure_ascii=False)

def rewrite_internal(p):
    key = p.strip("/").split("?")[0].split("#")[0]
    if key in PATH2FILE:
        return PATH2FILE[key]
    if key == "":
        return "index.html"
    return p  # ruta desconocida: dejar tal cual

if __name__ == "__main__":
    main()
