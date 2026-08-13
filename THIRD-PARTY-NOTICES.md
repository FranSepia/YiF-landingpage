# Avisos de terceros

Este sitio incluye software y fuentes de terceros. Cada componente conserva su
propia licencia, listada aquí completa. **Estos avisos deben viajar con
cualquier copia o redistribución del sitio** — es la condición que imponen las
licencias MIT y OFL.

Si algún día minificas o empaquetas el JS, configura la herramienta para
**preservar los comentarios de licencia** (`legal-comments` en esbuild,
`comments: /^!|@license|MIT/` en Terser). Quitarlos rompe el cumplimiento.

---

## 1. WebGL-Fluid-Simulation — el efecto de acuarela

El efecto que pinta el canvas al mover el cursor.
Origen: https://github.com/PavelDoGreat/WebGL-Fluid-Simulation

Dónde vive en este repo:

| Archivo | Forma |
|---|---|
| `site/assets/home/js/watercolor-home.js` | externo, lo carga `index.html` |
| `site/assets/soluciones/js/613b6a6361dc95d04258d19b_script.txt` | externo, lo cargan `soluciones.html` y `soluciones-copy.html` |
| las 8 páginas con fondo de fluido | copia **inline** dentro de su `<script>` |

Cada una de esas copias lleva el aviso completo al inicio. No lo borres.

```
MIT License

Copyright (c) 2017 Pavel Dobryakov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. jQuery 3.5.1

`site/assets/shared/js/jquery-3.5.1.min.dc5e7f18c8.js` · https://jquery.com

```
Copyright OpenJS Foundation and other contributors, https://openjsf.org/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 3. Splide

`site/assets/shared/js/splide.min.js`, `site/assets/shared/css/splide.min.css`
https://splidejs.com

```
Copyright (c) 2021 Naotoshi Fujita

Licensed under the MIT License. El texto completo de la MIT es el mismo
reproducido en la sección 1 de este documento.
```

---

## 4. Swiper

`site/assets/shared/js/swiper-bundle.min.js`, `site/assets/shared/css/swiper-bundle.min.css`
https://swiperjs.com

```
Copyright (c) 2014-2024 Vladimir Kharlampidi

Licensed under the MIT License. El texto completo de la MIT es el mismo
reproducido en la sección 1 de este documento.
```

---

## 5. Fuentes: Montserrat y Bitter

`site/assets/shared/fonts/` (woff2 auto-hospedados, sin llamadas a Google Fonts)

- **Montserrat** — © Julieta Ulanovsky y colaboradores
- **Bitter** — © Huerta Tipográfica

Ambas bajo **SIL Open Font License 1.1**
(https://scripts.sil.org/OFL). La OFL permite usarlas en un sitio comercial
sin costo. Lo único que prohíbe es **vender las fuentes por sí solas** y
**usar los nombres reservados** ("Montserrat", "Bitter") en versiones
modificadas.

---

## 6. Runtime de Webflow

`site/assets/shared/js/webflow.*.js` y el CSS `francos-radical-site-*.min.css`

Código generado y exportado desde Webflow para este sitio, bajo los términos
de servicio de Webflow del proyecto original. No es software de terceros
redistribuible por separado.

El badge "Made in Webflow" que inyecta el plan gratuito sigue presente. Ya no
usas Webflow, así que puedes quitarlo: busca `w-webflow-badge` en
`site/assets/shared/js/webflow.schunk.46f2c06d4a0bdbdb.js`, o añade
`.w-webflow-badge{display:none!important}` a tu CSS.
