(function () {
  'use strict';

  // --- 1) Inyecta contenedor y canvas fijo al fondo ---
  var holderId = 'fluid-bg-holder';
  var canvasId = 'fluid-bg-canvas';

  function ensureCanvas() {
    let holder = document.getElementById(holderId);
    if (!holder) {
      holder = document.createElement('div');
      holder.id = holderId;
      // Fijo, de pantalla completa, debajo de todo
      holder.style.position = 'fixed';
      holder.style.inset = '0';
      holder.style.zIndex = '0';
      holder.style.pointerEvents = 'none'; // no bloquea UI
      holder.style.userSelect = 'none';
      holder.style.touchAction = 'none';
      document.body.prepend(holder);
    }

    let canvas = document.getElementById(canvasId);
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = canvasId;
      canvas.style.width = '100vw';
      canvas.style.height = '100vh';
      canvas.style.display = 'block';
      holder.appendChild(canvas);
    }
    return canvas;
  }

  // Asegura que exista antes de seguir
  var canvas = ensureCanvas();

  // Re-crea si alguien lo quita/cambia
  var mo = new MutationObserver(function(){
    if (!document.getElementById(canvasId)) {
      canvas = ensureCanvas();
      boot(); // re-inicializa si lo removieron
    }
  });
  mo.observe(document.documentElement, { childList: true, subtree: true });

  // --- 2) CÓDIGO DE LA SIMULACIÓN (adaptado para Webflow fondo + menor brillo) ---

  function resizeCanvas () {
    const width = scaleByPixelRatio(window.innerWidth);
    const height = scaleByPixelRatio(window.innerHeight);
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      return true;
    }
    return false;
  }

  // Config base (bloom/sunrays desactivados; transparente; menos intensidad)
  var config = {
    SIM_RESOLUTION: 128,
    DYE_RESOLUTION: 768,
    CAPTURE_RESOLUTION: 512,
    DENSITY_DISSIPATION: 1.0,
    VELOCITY_DISSIPATION: 0.28,
    PRESSURE: 0.8,
    PRESSURE_ITERATIONS: 20,
    CURL: 20,
    SPLAT_RADIUS: 0.22,
    SPLAT_FORCE: 5000,
    SHADING: true,
    COLORFUL: true,
    COLOR_UPDATE_SPEED: 8,
    PAUSED: false,
    BACK_COLOR: { r: 0, g: 0, b: 0 },
    TRANSPARENT: true,   // <- clave para ver el sitio detrás
    BLOOM: false,        // <- brillo reducido (sin bloom)
    BLOOM_ITERATIONS: 6,
    BLOOM_RESOLUTION: 256,
    BLOOM_INTENSITY: 0.45,
    BLOOM_THRESHOLD: 0.7,
    BLOOM_SOFT_KNEE: 0.7,
    SUNRAYS: false,      // <- sin rayos
    SUNRAYS_RESOLUTION: 196,
    SUNRAYS_WEIGHT: 0.9
  };

  function pointerPrototype () {
    this.id = -1;
    this.texcoordX = 0;
    this.texcoordY = 0;
    this.prevTexcoordX = 0;
    this.prevTexcoordY = 0;
    this.deltaX = 0;
    this.deltaY = 0;
    this.down = false;
    this.moved = false;
    this.color = [30, 0, 300];
  }

  var pointers = [];
  var splatStack = [];
  pointers.push(new pointerPrototype());

  // === WebGL init ===
  var ref, gl, ext;
  function getWebGLContext (canvas) {
    var params = { alpha: true, depth: false, stencil: false, antialias: false, preserveDrawingBuffer: false };
    var gl2 = canvas.getContext('webgl2', params);
    var isWebGL2 = !!gl2;
    var gl = gl2 || canvas.getContext('webgl', params) || canvas.getContext('experimental-webgl', params);
    if (!gl) return null;

    var halfFloat;
    var supportLinearFiltering;
    if (isWebGL2) {
      gl.getExtension('EXT_color_buffer_float');
      supportLinearFiltering = gl.getExtension('OES_texture_float_linear');
    } else {
      halfFloat = gl.getExtension('OES_texture_half_float');
      supportLinearFiltering = gl.getExtension('OES_texture_half_float_linear');
    }

    gl.clearColor(0.0, 0.0, 0.0, 1.0);

    var halfFloatTexType = isWebGL2 ? gl.HALF_FLOAT : (halfFloat && halfFloat.HALF_FLOAT_OES);
    var formatRGBA, formatRG, formatR;

    function getSupportedFormat (gl, internalFormat, format, type) {
      if (!supportRenderTextureFormat(gl, internalFormat, format, type)) {
        switch (internalFormat) {
          case gl.R16F: return getSupportedFormat(gl, gl.RG16F, gl.RG, type);
          case gl.RG16F: return getSupportedFormat(gl, gl.RGBA16F, gl.RGBA, type);
          default: return null;
        }
      }
      return { internalFormat: internalFormat, format: format };
    }
    function supportRenderTextureFormat (gl, internalFormat, format, type) {
      var texture = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, 4, 4, 0, format, type, null);
      var fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
      var status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      return status == gl.FRAMEBUFFER_COMPLETE;
    }

    if (isWebGL2) {
      formatRGBA = getSupportedFormat(gl, gl.RGBA16F, gl.RGBA, halfFloatTexType);
      formatRG = getSupportedFormat(gl, gl.RG16F, gl.RG, halfFloatTexType);
      formatR = getSupportedFormat(gl, gl.R16F, gl.RED, halfFloatTexType);
    } else {
      formatRGBA = getSupportedFormat(gl, gl.RGBA, gl.RGBA, halfFloatTexType);
      formatRG   = formatRGBA;
      formatR    = formatRGBA;
    }

    return {
      gl: gl,
      ext: {
        formatRGBA: formatRGBA,
        formatRG: formatRG,
        formatR: formatR,
        halfFloatTexType: halfFloatTexType,
        supportLinearFiltering: !!supportLinearFiltering
      }
    };
  }

  function isMobile () { return /Mobi|Android/i.test(navigator.userAgent); }

  // Shaders util
  var Material = function Material (vertexShader, fragmentShaderSource) {
    this.vertexShader = vertexShader;
    this.fragmentShaderSource = fragmentShaderSource;
    this.programs = [];
    this.activeProgram = null;
    this.uniforms = [];
  };
  Material.prototype.setKeywords = function (keywords) {
    var hash = 0;
    for (var i = 0; i < keywords.length; i++) hash += hashCode(keywords[i]);
    var program = this.programs[hash];
    if (program == null) {
      var fragmentShader = compileShader(gl.FRAGMENT_SHADER, this.fragmentShaderSource, keywords);
      program = createProgram(this.vertexShader, fragmentShader);
      this.programs[hash] = program;
    }
    if (program == this.activeProgram) return;
    this.uniforms = getUniforms(program);
    this.activeProgram = program;
  };
  Material.prototype.bind = function () { gl.useProgram(this.activeProgram); };

  var Program = function Program (vertexShader, fragmentShader) {
    this.uniforms = {};
    this.program = createProgram(vertexShader, fragmentShader);
    this.uniforms = getUniforms(this.program);
  };
  Program.prototype.bind = function () { gl.useProgram(this.program); };

  function createProgram (vertexShader, fragmentShader) {
    var program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw gl.getProgramInfoLog(program);
    return program;
  }
  function getUniforms (program) {
    var uniforms = [];
    var uniformCount = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
    for (var i = 0; i < uniformCount; i++) {
      var uniformName = gl.getActiveUniform(program, i).name;
      uniforms[uniformName] = gl.getUniformLocation(program, uniformName);
    }
    return uniforms;
  }
  function compileShader (type, source, keywords) {
    source = addKeywords(source, keywords);
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(shader);
    return shader;
  }
  function addKeywords (source, keywords) {
    if (keywords == null) return source;
    var out = '';
    keywords.forEach(function (k) { out += '#define ' + k + '\n'; });
    return out + source;
  }

  // Vertex shaders
  var baseVertexShader = null;
  var blurVertexShader = null;

  // Fragment shader sources (idénticos a los del script original, salvo que BLOOM/SUNRAYS pueden quedar off por config)
  var blurShader, copyShader, clearShader, colorShader, checkerboardShader,
      bloomPrefilterShader, bloomBlurShader, bloomFinalShader,
      sunraysMaskShader, sunraysShader, splatShader, advectionShader,
      divergenceShader, curlShader, vorticityShader, pressureShader, gradientSubtractShader,
      displayShaderSource;

  // Buffers/targets
  var dye, velocity, divergence, curl, pressure, bloom, bloomFramebuffers = [], sunrays, sunraysTemp;
  var ditheringTexture = null; // no usado si BLOOM=false

  var blurProgram, copyProgram, clearProgram, colorProgram, checkerboardProgram,
      bloomPrefilterProgram, bloomBlurProgram, bloomFinalProgram,
      sunraysMaskProgram, sunraysProgram, splatProgram, advectionProgram,
      divergenceProgram, curlProgram, vorticityProgram, pressureProgram, gradienSubtractProgram;

  var displayMaterial;

  // Utilidades varias del original
  function framebufferToTexture (target) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo);
    var length = target.width * target.height * 4;
    var texture = new Float32Array(length);
    gl.readPixels(0, 0, target.width, target.height, gl.RGBA, gl.FLOAT, texture);
    return texture;
  }
  function normalizeTexture (texture, width, height) {
    var result = new Uint8Array(texture.length);
    var id = 0;
    for (var i = height - 1; i >= 0; i--) {
      for (var j = 0; j < width; j++) {
        var nid = i * width * 4 + j * 4;
        result[nid + 0] = clamp01(texture[id + 0]) * 255;
        result[nid + 1] = clamp01(texture[id + 1]) * 255;
        result[nid + 2] = clamp01(texture[id + 2]) * 255;
        result[nid + 3] = clamp01(texture[id + 3]) * 255;
        id += 4;
      }
    }
    return result;
  }
  function clamp01 (x) { return Math.min(Math.max(x, 0), 1); }

  function createFBO (w, h, internalFormat, format, type, param) {
    gl.activeTexture(gl.TEXTURE0);
    var texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, param);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, param);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, w, h, 0, format, type, null);

    var fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
    gl.viewport(0, 0, w, h);
    gl.clear(gl.COLOR_BUFFER_BIT);

    var texelSizeX = 1.0 / w;
    var texelSizeY = 1.0 / h;

    return {
      texture: texture,
      fbo: fbo,
      width: w,
      height: h,
      texelSizeX: texelSizeX,
      texelSizeY: texelSizeY,
      attach: function (id) {
        gl.activeTexture(gl.TEXTURE0 + id);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        return id;
      }
    };
  }
  function createDoubleFBO (w, h, internalFormat, format, type, param) {
    var fbo1 = createFBO(w, h, internalFormat, format, type, param);
    var fbo2 = createFBO(w, h, internalFormat, format, type, param);
    return {
      width: w, height: h,
      texelSizeX: fbo1.texelSizeX, texelSizeY: fbo1.texelSizeY,
      get read () { return fbo1; }, set read (v) { fbo1 = v; },
      get write () { return fbo2; }, set write (v) { fbo2 = v; },
      swap: function () { var t = fbo1; fbo1 = fbo2; fbo2 = t; }
    };
  }
  function resizeFBO (target, w, h, internalFormat, format, type, param) {
    var newFBO = createFBO(w, h, internalFormat, format, type, param);
    copyProgram.bind();
    gl.uniform1i(copyProgram.uniforms.uTexture, target.attach(0));
    blit(newFBO.fbo);
    return newFBO;
  }
  function resizeDoubleFBO (target, w, h, internalFormat, format, type, param) {
    if (target.width == w && target.height == h) return target;
    target.read  = resizeFBO(target.read,  w, h, internalFormat, format, type, param);
    target.write = createFBO(w, h, internalFormat, format, type, param);
    target.width = w; target.height = h;
    target.texelSizeX = 1.0 / w; target.texelSizeY = 1.0 / h;
    return target;
  }

  var blit = null;

  function updateKeywords () {
    var displayKeywords = [];
    if (config.SHADING) displayKeywords.push("SHADING");
    if (config.BLOOM)   displayKeywords.push("BLOOM");
    if (config.SUNRAYS) displayKeywords.push("SUNRAYS");
    displayMaterial.setKeywords(displayKeywords);
  }

  function getResolution (resolution) {
    var aspectRatio = gl.drawingBufferWidth / gl.drawingBufferHeight;
    if (aspectRatio < 1) aspectRatio = 1.0 / aspectRatio;
    var min = Math.round(resolution);
    var max = Math.round(resolution * aspectRatio);
    if (gl.drawingBufferWidth > gl.drawingBufferHeight) return { width: max, height: min };
    else return { width: min, height: max };
  }
  function getTextureScale (texture, width, height) {
    return { x: width / texture.width, y: height / texture.height };
  }
  function scaleByPixelRatio (input) {
    var pixelRatio = window.devicePixelRatio || 1;
    return Math.floor(input * pixelRatio);
  }
  function hashCode (s) {
    if (!s || s.length == 0) return 0;
    var hash = 0;
    for (var i = 0; i < s.length; i++) { hash = (hash << 5) - hash + s.charCodeAt(i); hash |= 0; }
    return hash;
  }
  function wrap (value, min, max) {
    var range = max - min; if (range == 0) return min;
    return (value - min) % range + min;
  }
  function normalizeColor (input) {
    return { r: input.r / 255, g: input.g / 255, b: input.b / 255 };
  }
  function HSVtoRGB (h, s, v) {
    var r, g, b, i, f, p, q, t;
    i = Math.floor(h * 6); f = h * 6 - i;
    p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s);
    switch (i % 6) {
      case 0: r=v; g=t; b=p; break;
      case 1: r=q; g=v; b=p; break;
      case 2: r=p; g=v; b=t; break;
      case 3: r=p; g=q; b=v; break;
      case 4: r=t; g=p; b=v; break;
      case 5: r=v; g=p; b=q; break;
    }
    return { r:r, g:g, b:b };
  }
  function generateColor () {
    var c = HSVtoRGB(Math.random(), 1.0, 1.0);
    // Menos brillo global
    c.r *= 0.08; c.g *= 0.08; c.b *= 0.08;
    return c;
  }

  // === Build shaders ===
  function buildShaders() {
    baseVertexShader = compileShader(gl.VERTEX_SHADER, `
      precision highp float;
      attribute vec2 aPosition;
      varying vec2 vUv;
      varying vec2 vL;
      varying vec2 vR;
      varying vec2 vT;
      varying vec2 vB;
      uniform vec2 texelSize;
      void main () {
        vUv = aPosition * 0.5 + 0.5;
        vL = vUv - vec2(texelSize.x, 0.0);
        vR = vUv + vec2(texelSize.x, 0.0);
        vT = vUv + vec2(0.0, texelSize.y);
        vB = vUv - vec2(0.0, texelSize.y);
        gl_Position = vec4(aPosition, 0.0, 1.0);
      }
    `);
    blurVertexShader = compileShader(gl.VERTEX_SHADER, `
      precision highp float;
      attribute vec2 aPosition;
      varying vec2 vUv;
      varying vec2 vL;
      varying vec2 vR;
      uniform vec2 texelSize;
      void main () {
        vUv = aPosition * 0.5 + 0.5;
        float offset = 1.33333333;
        vL = vUv - texelSize * offset;
        vR = vUv + texelSize * offset;
        gl_Position = vec4(aPosition, 0.0, 1.0);
      }
    `);

    blurShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float;
      precision mediump sampler2D;
      varying vec2 vUv; varying vec2 vL; varying vec2 vR;
      uniform sampler2D uTexture;
      void main(){
        vec4 sum = texture2D(uTexture, vUv) * 0.29411764;
        sum += texture2D(uTexture, vL) * 0.35294117;
        sum += texture2D(uTexture, vR) * 0.35294117;
        gl_FragColor = sum;
      }
    `);
    copyShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float;
      precision mediump sampler2D;
      varying highp vec2 vUv;
      uniform sampler2D uTexture;
      void main(){ gl_FragColor = texture2D(uTexture, vUv); }
    `);
    clearShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying highp vec2 vUv;
      uniform sampler2D uTexture; uniform float value;
      void main(){ gl_FragColor = value * texture2D(uTexture, vUv); }
    `);
    colorShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; uniform vec4 color;
      void main(){ gl_FragColor = color; }
    `);
    checkerboardShader = compileShader(gl.FRAGMENT_SHADER, `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; uniform sampler2D uTexture; uniform float aspectRatio;
      #define SCALE 25.0
      void main(){
        vec2 uv = floor(vUv * SCALE * vec2(aspectRatio, 1.0));
        float v = mod(uv.x + uv.y, 2.0); v = v * 0.1 + 0.8;
        gl_FragColor = vec4(vec3(v), 1.0);
      }
    `);
    displayShaderSource = `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB;
      uniform sampler2D uTexture; uniform sampler2D uBloom; uniform sampler2D uSunrays; uniform sampler2D uDithering;
      uniform vec2 ditherScale; uniform vec2 texelSize;
      vec3 linearToGamma (vec3 color) {
        color = max(color, vec3(0)); return max(1.055 * pow(color, vec3(0.416666667)) - 0.055, vec3(0));
      }
      void main () {
        vec3 c = texture2D(uTexture, vUv).rgb;
      #ifdef SHADING
        vec3 lc = texture2D(uTexture, vL).rgb;
        vec3 rc = texture2D(uTexture, vR).rgb;
        vec3 tc = texture2D(uTexture, vT).rgb;
        vec3 bc = texture2D(uTexture, vB).rgb;
        float dx = length(rc) - length(lc);
        float dy = length(tc) - length(bc);
        vec3 n = normalize(vec3(dx, dy, length(texelSize)));
        vec3 l = vec3(0.0, 0.0, 1.0);
        float diffuse = clamp(dot(n, l) + 0.7, 0.7, 1.0);
        c *= diffuse;
      #endif
      #ifdef BLOOM
        vec3 bloom = texture2D(uBloom, vUv).rgb;
      #endif
      #ifdef SUNRAYS
        float sunrays = texture2D(uSunrays, vUv).r;
        c *= sunrays;
      #ifdef BLOOM
        bloom *= sunrays;
      #endif
      #endif
      #ifdef BLOOM
        float noise = texture2D(uDithering, vUv * ditherScale).r;
        noise = noise * 2.0 - 1.0;
        bloom += noise / 255.0;
        bloom = linearToGamma(bloom);
        c += bloom;
      #endif
        float a = max(c.r, max(c.g, c.b));
        gl_FragColor = vec4(c, a);
      }
    `;
    bloomPrefilterShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying vec2 vUv; uniform sampler2D uTexture; uniform vec3 curve; uniform float threshold;
      void main(){
        vec3 c = texture2D(uTexture, vUv).rgb;
        float br = max(c.r, max(c.g, c.b));
        float rq = clamp(br - curve.x, 0.0, curve.y);
        rq = curve.z * rq * rq;
        c *= max(rq, br - threshold) / max(br, 0.0001);
        gl_FragColor = vec4(c, 0.0);
      }
    `);
    bloomBlurShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB;
      uniform sampler2D uTexture;
      void main(){
        vec4 sum = vec4(0.0);
        sum += texture2D(uTexture, vL);
        sum += texture2D(uTexture, vR);
        sum += texture2D(uTexture, vT);
        sum += texture2D(uTexture, vB);
        sum *= 0.25;
        gl_FragColor = sum;
      }
    `);
    bloomFinalShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB;
      uniform sampler2D uTexture; uniform float intensity;
      void main(){
        vec4 sum = vec4(0.0);
        sum += texture2D(uTexture, vL);
        sum += texture2D(uTexture, vR);
        sum += texture2D(uTexture, vT);
        sum += texture2D(uTexture, vB);
        sum *= 0.25;
        gl_FragColor = sum * intensity;
      }
    `);
    sunraysMaskShader = compileShader(gl.FRAGMENT_SHADER, `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; uniform sampler2D uTexture;
      void main(){
        vec4 c = texture2D(uTexture, vUv);
        float br = max(c.r, max(c.g, c.b));
        c.a = 1.0 - min(max(br * 20.0, 0.0), 0.8);
        gl_FragColor = c;
      }
    `);
    sunraysShader = compileShader(gl.FRAGMENT_SHADER, `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; uniform sampler2D uTexture; uniform float weight;
      #define ITERATIONS 16
      void main(){
        float Density = 0.3; float Decay = 0.95; float Exposure = 0.7;
        vec2 coord = vUv; vec2 dir = vUv - 0.5;
        dir *= 1.0 / float(ITERATIONS) * Density;
        float illuminationDecay = 1.0;
        float color = texture2D(uTexture, vUv).a;
        for (int i = 0; i < ITERATIONS; i++){
          coord -= dir;
          float col = texture2D(uTexture, coord).a;
          color += col * illuminationDecay * weight;
          illuminationDecay *= Decay;
        }
        gl_FragColor = vec4(color * Exposure, 0.0, 0.0, 1.0);
      }
    `);
    splatShader = compileShader(gl.FRAGMENT_SHADER, `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; uniform sampler2D uTarget; uniform float aspectRatio;
      uniform vec3 color; uniform vec2 point; uniform float radius;
      void main(){
        vec2 p = vUv - point.xy;
        p.x *= aspectRatio;
        vec3 splat = exp(-dot(p,p) / radius) * color;
        vec3 base = texture2D(uTarget, vUv).xyz;
        gl_FragColor = vec4(base + splat, 1.0);
      }
    `);
    advectionShader = compileShader(gl.FRAGMENT_SHADER, `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; uniform sampler2D uVelocity; uniform sampler2D uSource;
      uniform vec2 texelSize; uniform vec2 dyeTexelSize; uniform float dt; uniform float dissipation;
      vec4 bilerp (sampler2D sam, vec2 uv, vec2 tsize) {
        vec2 st = uv / tsize - 0.5;
        vec2 iuv = floor(st); vec2 fuv = fract(st);
        vec4 a = texture2D(sam, (iuv + vec2(0.5, 0.5)) * tsize);
        vec4 b = texture2D(sam, (iuv + vec2(1.5, 0.5)) * tsize);
        vec4 c = texture2D(sam, (iuv + vec2(0.5, 1.5)) * tsize);
        vec4 d = texture2D(sam, (iuv + vec2(1.5, 1.5)) * tsize);
        return mix(mix(a,b,fuv.x), mix(c,d,fuv.x), fuv.y);
      }
      void main(){
      #ifdef MANUAL_FILTERING
        vec2 coord = vUv - dt * bilerp(uVelocity, vUv, texelSize).xy * texelSize;
        vec4 result = bilerp(uSource, coord, dyeTexelSize);
      #else
        vec2 coord = vUv - dt * texture2D(uVelocity, vUv).xy * texelSize;
        vec4 result = texture2D(uSource, coord);
      #endif
        float decay = 1.0 + dissipation * dt;
        gl_FragColor = result / decay;
      }
    `, null);

    divergenceShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying highp vec2 vUv; varying highp vec2 vL; varying highp vec2 vR; varying highp vec2 vT; varying highp vec2 vB;
      uniform sampler2D uVelocity;
      void main(){
        float L = texture2D(uVelocity, vL).x;
        float R = texture2D(uVelocity, vR).x;
        float T = texture2D(uVelocity, vT).y;
        float B = texture2D(uVelocity, vB).y;
        vec2 C = texture2D(uVelocity, vUv).xy;
        if (vL.x < 0.0) L = -C.x;
        if (vR.x > 1.0) R = -C.x;
        if (vT.y > 1.0) T = -C.y;
        if (vB.y < 0.0) B = -C.y;
        float div = 0.5 * (R - L + T - B);
        gl_FragColor = vec4(div, 0.0, 0.0, 1.0);
      }
    `);
    curlShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying highp vec2 vUv; varying highp vec2 vL; varying highp vec2 vR; varying highp vec2 vT; varying highp vec2 vB;
      uniform sampler2D uVelocity;
      void main(){
        float L = texture2D(uVelocity, vL).y;
        float R = texture2D(uVelocity, vR).y;
        float T = texture2D(uVelocity, vT).x;
        float B = texture2D(uVelocity, vB).x;
        float vorticity = R - L - T + B;
        gl_FragColor = vec4(0.5 * vorticity, 0.0, 0.0, 1.0);
      }
    `);
    vorticityShader = compileShader(gl.FRAGMENT_SHADER, `
      precision highp float; precision highp sampler2D;
      varying vec2 vUv; varying vec2 vL; varying vec2 vR; varying vec2 vT; varying vec2 vB;
      uniform sampler2D uVelocity; uniform sampler2D uCurl; uniform float curl; uniform float dt;
      void main(){
        float L = texture2D(uCurl, vL).x;
        float R = texture2D(uCurl, vR).x;
        float T = texture2D(uCurl, vT).x;
        float B = texture2D(uCurl, vB).x;
        float C = texture2D(uCurl, vUv).x;
        vec2 force = 0.5 * vec2(abs(T) - abs(B), abs(R) - abs(L));
        force /= length(force) + 0.0001;
        force *= curl * C;
        force.y *= -1.0;
        vec2 vel = texture2D(uVelocity, vUv).xy;
        gl_FragColor = vec4(vel + force * dt, 0.0, 1.0);
      }
    `);
    pressureShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying highp vec2 vUv; varying highp vec2 vL; varying highp vec2 vR; varying highp vec2 vT; varying highp vec2 vB;
      uniform sampler2D uPressure; uniform sampler2D uDivergence;
      void main(){
        float L = texture2D(uPressure, vL).x;
        float R = texture2D(uPressure, vR).x;
        float T = texture2D(uPressure, vT).x;
        float B = texture2D(uPressure, vB).x;
        float divergence = texture2D(uDivergence, vUv).x;
        float pressure = (L + R + B + T - divergence) * 0.25;
        gl_FragColor = vec4(pressure, 0.0, 0.0, 1.0);
      }
    `);
    gradientSubtractShader = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float; precision mediump sampler2D;
      varying highp vec2 vUv; varying highp vec2 vL; varying highp vec2 vR; varying highp vec2 vT; varying highp vec2 vB;
      uniform sampler2D uPressure; uniform sampler2D uVelocity;
      void main(){
        float L = texture2D(uPressure, vL).x;
        float R = texture2D(uPressure, vR).x;
        float T = texture2D(uPressure, vT).x;
        float B = texture2D(uPressure, vB).x;
        vec2 velocity = texture2D(uVelocity, vUv).xy;
        velocity.xy -= vec2(R - L, T - B);
        gl_FragColor = vec4(velocity, 0.0, 1.0);
      }
    `);
  }

  function initProgramsAndFBOs() {
    // Programs
    blurProgram            = new Program(blurVertexShader, blurShader);
    copyProgram            = new Program(baseVertexShader, copyShader);
    clearProgram           = new Program(baseVertexShader, clearShader);
    colorProgram           = new Program(baseVertexShader, colorShader);
    checkerboardProgram    = new Program(baseVertexShader, checkerboardShader);
    bloomPrefilterProgram  = new Program(baseVertexShader, bloomPrefilterShader);
    bloomBlurProgram       = new Program(baseVertexShader, bloomBlurShader);
    bloomFinalProgram      = new Program(baseVertexShader, bloomFinalShader);
    sunraysMaskProgram     = new Program(baseVertexShader, sunraysMaskShader);
    sunraysProgram         = new Program(baseVertexShader, sunraysShader);
    splatProgram           = new Program(baseVertexShader, splatShader);
    advectionProgram       = new Program(baseVertexShader, advectionShader);
    divergenceProgram      = new Program(baseVertexShader, divergenceShader);
    curlProgram            = new Program(baseVertexShader, curlShader);
    vorticityProgram       = new Program(baseVertexShader, vorticityShader);
    pressureProgram        = new Program(baseVertexShader, pressureShader);
    gradienSubtractProgram = new Program(baseVertexShader, gradientSubtractShader);

    displayMaterial = new Material(baseVertexShader, displayShaderSource);

    // Quad buffer
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, -1,1, 1,1, 1,-1]), gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array([0,1,2, 0,2,3]), gl.STATIC_DRAW);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(0);

    blit = function (destination) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, destination);
      gl.drawElements(gl.TRIANGLES, 6, gl.UNSIGNED_SHORT, 0);
    };

    updateKeywords();
    initFramebuffers();
  }

  function initFramebuffers () {
    var simRes = getResolution(config.SIM_RESOLUTION);
    var dyeRes = getResolution(config.DYE_RESOLUTION);
    var texType = ext.halfFloatTexType;
    var rgba    = ext.formatRGBA;
    var rg      = ext.formatRG;
    var r       = ext.formatR;
    var filtering = ext.supportLinearFiltering ? gl.LINEAR : gl.NEAREST;

    if (dye == null) dye = createDoubleFBO(dyeRes.width, dyeRes.height, rgba.internalFormat, rgba.format, texType, filtering);
    else             dye = resizeDoubleFBO(dye, dyeRes.width, dyeRes.height, rgba.internalFormat, rgba.format, texType, filtering);

    if (velocity == null) velocity = createDoubleFBO(simRes.width, simRes.height, rg.internalFormat, rg.format, texType, filtering);
    else                  velocity = resizeDoubleFBO(velocity, simRes.width, simRes.height, rg.internalFormat, rg.format, texType, filtering);

    divergence = createFBO(simRes.width, simRes.height, r.internalFormat, r.format, texType, gl.NEAREST);
    curl       = createFBO(simRes.width, simRes.height, r.internalFormat, r.format, texType, gl.NEAREST);
    pressure   = createDoubleFBO(simRes.width, simRes.height, r.internalFormat, r.format, texType, gl.NEAREST);

    if (config.BLOOM) initBloomFramebuffers();
    if (config.SUNRAYS) initSunraysFramebuffers();
  }
  function initBloomFramebuffers () {
    var res = getResolution(config.BLOOM_RESOLUTION);
    var texType = ext.halfFloatTexType;
    var rgba = ext.formatRGBA;
    var filtering = ext.supportLinearFiltering ? gl.LINEAR : gl.NEAREST;
    bloom = createFBO(res.width, res.height, rgba.internalFormat, rgba.format, texType, filtering);
    bloomFramebuffers.length = 0;
    for (var i = 0; i < config.BLOOM_ITERATIONS; i++) {
      var width = res.width >> (i + 1);
      var height = res.height >> (i + 1);
      if (width < 2 || height < 2) break;
      var fbo = createFBO(width, height, rgba.internalFormat, rgba.format, texType, filtering);
      bloomFramebuffers.push(fbo);
    }
  }
  function initSunraysFramebuffers () {
    var res = getResolution(config.SUNRAYS_RESOLUTION);
    var texType = ext.halfFloatTexType;
    var r = ext.formatR;
    var filtering = ext.supportLinearFiltering ? gl.LINEAR : gl.NEAREST;
    sunrays     = createFBO(res.width, res.height, r.internalFormat, r.format, texType, filtering);
    sunraysTemp = createFBO(res.width, res.height, r.internalFormat, r.format, texType, filtering);
  }

  function applyBloom (source, destination) {
    if (!config.BLOOM || bloomFramebuffers.length < 2) return;
    var last = destination;
    gl.disable(gl.BLEND);
    bloomPrefilterProgram.bind();
    var knee = config.BLOOM_THRESHOLD * config.BLOOM_SOFT_KNEE + 0.0001;
    var curve0 = config.BLOOM_THRESHOLD - knee;
    var curve1 = knee * 2;
    var curve2 = 0.25 / knee;
    gl.uniform3f(bloomPrefilterProgram.uniforms.curve, curve0, curve1, curve2);
    gl.uniform1f(bloomPrefilterProgram.uniforms.threshold, config.BLOOM_THRESHOLD);
    gl.uniform1i(bloomPrefilterProgram.uniforms.uTexture, source.attach(0));
    gl.viewport(0, 0, last.width, last.height);
    blit(last.fbo);

    bloomBlurProgram.bind();
    for (var i = 0; i < bloomFramebuffers.length; i++) {
      var dest = bloomFramebuffers[i];
      gl.uniform2f(bloomBlurProgram.uniforms.texelSize, last.texelSizeX, last.texelSizeY);
      gl.uniform1i(bloomBlurProgram.uniforms.uTexture, last.attach(0));
      gl.viewport(0, 0, dest.width, dest.height);
      blit(dest.fbo);
      last = dest;
    }

    gl.blendFunc(gl.ONE, gl.ONE); gl.enable(gl.BLEND);
    for (var j = bloomFramebuffers.length - 2; j >= 0; j--) {
      var baseTex = bloomFramebuffers[j];
      gl.uniform2f(bloomBlurProgram.uniforms.texelSize, last.texelSizeX, last.texelSizeY);
      gl.uniform1i(bloomBlurProgram.uniforms.uTexture, last.attach(0));
      gl.viewport(0, 0, baseTex.width, baseTex.height);
      blit(baseTex.fbo);
      last = baseTex;
    }

    gl.disable(gl.BLEND);
    bloomFinalProgram.bind();
    gl.uniform2f(bloomFinalProgram.uniforms.texelSize, last.texelSizeX, last.texelSizeY);
    gl.uniform1i(bloomFinalProgram.uniforms.uTexture, last.attach(0));
    gl.uniform1f(bloomFinalProgram.uniforms.intensity, config.BLOOM_INTENSITY);
    gl.viewport(0, 0, destination.width, destination.height);
    blit(destination.fbo);
  }

  function applySunrays (source, mask, destination) {
    if (!config.SUNRAYS) return;
    gl.disable(gl.BLEND);
    sunraysMaskProgram.bind();
    gl.uniform1i(sunraysMaskProgram.uniforms.uTexture, source.attach(0));
    gl.viewport(0, 0, mask.width, mask.height);
    blit(mask.fbo);
    sunraysProgram.bind();
    gl.uniform1f(sunraysProgram.uniforms.weight, config.SUNRAYS_WEIGHT);
    gl.uniform1i(sunraysProgram.uniforms.uTexture, mask.attach(0));
    gl.viewport(0, 0, destination.width, destination.height);
    blit(destination.fbo);
  }

  function drawColor (fbo, color) {
    colorProgram.bind();
    gl.uniform4f(colorProgram.uniforms.color, color.r, color.g, color.b, 1);
    blit(fbo);
  }
  function drawCheckerboard (fbo) {
    checkerboardProgram.bind();
    gl.uniform1f(checkerboardProgram.uniforms.aspectRatio, canvas.width / canvas.height);
    blit(fbo);
  }
  function drawDisplay (fbo, width, height) {
    displayMaterial.bind();
    if (config.SHADING) gl.uniform2f(displayMaterial.uniforms.texelSize, 1.0 / width, 1.0 / height);
    gl.uniform1i(displayMaterial.uniforms.uTexture, dye.read.attach(0));
    if (config.BLOOM) {
      gl.uniform1i(displayMaterial.uniforms.uBloom, bloom.attach(1));
      // Dithering deshabilitado por no usar textura externa
      // gl.uniform1i(displayMaterial.uniforms.uDithering, ditheringTexture.attach(2));
      var scale = {x:1,y:1};
      gl.uniform2f(displayMaterial.uniforms.ditherScale, scale.x, scale.y);
    }
    if (config.SUNRAYS) gl.uniform1i(displayMaterial.uniforms.uSunrays, sunrays.attach(3));
    blit(fbo);
  }
  function render (target) {
    if (config.BLOOM) applyBloom(dye.read, bloom);
    if (config.SUNRAYS) { applySunrays(dye.read, dye.write, sunrays); blur(sunrays, sunraysTemp, 1); }
    
    else gl.disable(gl.BLEND);

    var width = target == null ? gl.drawingBufferWidth : target.width;
    var height = target == null ? gl.drawingBufferHeight : target.height;
    gl.viewport(0, 0, width, height);

    var fbo = target == null ? null : target.fbo;
    if (!config.TRANSPARENT) drawColor(fbo, normalizeColor(config.BACK_COLOR));
    if (target == null && config.TRANSPARENT) drawCheckerboard(fbo);
    drawDisplay(fbo, width, height);
  }
  function blur (target, temp, iterations) {
    blurProgram.bind();
    for (var i = 0; i < iterations; i++) {
      gl.uniform2f(blurProgram.uniforms.texelSize, target.texelSizeX, 0.0);
      gl.uniform1i(blurProgram.uniforms.uTexture, target.attach(0));
      blit(temp.fbo);
      gl.uniform2f(blurProgram.uniforms.texelSize, 0.0, target.texelSizeY);
      gl.uniform1i(blurProgram.uniforms.uTexture, temp.attach(0));
      blit(target.fbo);
    }
  }
  function correctRadius (radius) { var aspectRatio = canvas.width / canvas.height; if (aspectRatio > 1) radius *= aspectRatio; return radius; }

  function splat (x, y, dx, dy, color) {
    gl.viewport(0, 0, velocity.width, velocity.height);
    splatProgram.bind();
    gl.uniform1i(splatProgram.uniforms.uTarget, velocity.read.attach(0));
    gl.uniform1f(splatProgram.uniforms.aspectRatio, canvas.width / canvas.height);
    gl.uniform2f(splatProgram.uniforms.point, x, y);
    gl.uniform3f(splatProgram.uniforms.color, dx, dy, 0.0);
    gl.uniform1f(splatProgram.uniforms.radius, correctRadius(config.SPLAT_RADIUS / 100.0));
    blit(velocity.write.fbo);
    velocity.swap();

    gl.viewport(0, 0, dye.width, dye.height);
    gl.uniform1i(splatProgram.uniforms.uTarget, dye.read.attach(0));
    gl.uniform3f(splatProgram.uniforms.color, color.r, color.g, color.b);
    blit(dye.write.fbo);
    dye.swap();
  }
  function multipleSplats (amount) {
    for (var i = 0; i < amount; i++) {
      var color = generateColor();
      color.r *= 10.0; color.g *= 10.0; color.b *= 10.0;
      var x = Math.random(); var y = Math.random();
      var dx = 1000 * (Math.random() - 0.5);
      var dy = 1000 * (Math.random() - 0.5);
      splat(x, y, dx, dy, color);
    }
  }
  function splatPointer (pointer) {
    var dx = pointer.deltaX * config.SPLAT_FORCE;
    var dy = pointer.deltaY * config.SPLAT_FORCE;
    splat(pointer.texcoordX, pointer.texcoordY, dx, dy, pointer.color);
  }

  // ===== INPUTS (en window, para que funcione aunque el canvas no reciba eventos) =====
  function canvasCoordsFromClient(clientX, clientY) {
    var rect = { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
    var posX = scaleByPixelRatio(clientX - rect.left);
    var posY = scaleByPixelRatio(clientY - rect.top);
    return { x: posX, y: posY };
  }
  function updatePointerDownData (pointer, id, posX, posY) {
    pointer.id = id; pointer.down = true; pointer.moved = false;
    pointer.texcoordX = posX / canvas.width;
    pointer.texcoordY = 1.0 - posY / canvas.height;
    pointer.prevTexcoordX = pointer.texcoordX;
    pointer.prevTexcoordY = pointer.texcoordY;
    pointer.deltaX = 0; pointer.deltaY = 0;
    pointer.color = generateColor();
  }
  function correctDeltaX (delta) {
    var aspectRatio = canvas.width / canvas.height;
    if (aspectRatio < 1) delta *= aspectRatio;
    return delta;
  }
  function correctDeltaY (delta) {
    var aspectRatio = canvas.width / canvas.height;
    if (aspectRatio > 1) delta /= aspectRatio;
    return delta;
  }
  function updatePointerMoveData (pointer, posX, posY) {
    pointer.prevTexcoordX = pointer.texcoordX;
    pointer.prevTexcoordY = pointer.texcoordY;
    pointer.texcoordX = posX / canvas.width;
    pointer.texcoordY = 1.0 - posY / canvas.height;
    pointer.deltaX = correctDeltaX(pointer.texcoordX - pointer.prevTexcoordX);
    pointer.deltaY = correctDeltaY(pointer.texcoordY - pointer.prevTexcoordY);
    pointer.moved = Math.abs(pointer.deltaX) > 0 || Math.abs(pointer.deltaY) > 0;
  }
  function updatePointerUpData (pointer) { pointer.down = false; }

  // Eventos en window/document para no bloquear UI ni depender del canvas
  window.addEventListener('mousedown', function (e) {
    const { x, y } = canvasCoordsFromClient(e.clientX, e.clientY);
    var pointer = pointers.find(function (p) { return p.id == -1; }) || new pointerPrototype();
    updatePointerDownData(pointer, -1, x, y);
    if (!pointers.includes(pointer)) pointers.push(pointer);
  }, { passive: true });

window.addEventListener('mousemove', function (e) {
  var pointer = pointers[0];
  const { x, y } = canvasCoordsFromClient(e.clientX, e.clientY);

  if (!pointer.down) {
    updatePointerDownData(pointer, -1, x, y);
  }

  updatePointerMoveData(pointer, x, y);
}, { passive: true });

  window.addEventListener('mouseup', function () { updatePointerUpData(pointers[0]); }, { passive: true });

  window.addEventListener('touchstart', function (e) {
    const touches = e.changedTouches;
    while (touches.length >= pointers.length) pointers.push(new pointerPrototype());
    for (var i = 0; i < touches.length; i++) {
      const { x, y } = canvasCoordsFromClient(touches[i].clientX, touches[i].clientY);
      updatePointerDownData(pointers[i + 1], touches[i].identifier, x, y);
    }
  }, { passive: true });

  window.addEventListener('touchmove', function (e) {
    const touches = e.changedTouches;
    for (var i = 0; i < touches.length; i++) {
      var pointer = pointers[i + 1]; if (!pointer || !pointer.down) continue;
      const { x, y } = canvasCoordsFromClient(touches[i].clientX, touches[i].clientY);
      updatePointerMoveData(pointer, x, y);
    }
  }, { passive: true });

  window.addEventListener('touchend', function (e) {
    const touches = e.changedTouches;
    for (var i = 0; i < touches.length; i++) {
      var pointer = pointers.find(function (p) { return p.id == touches[i].identifier; });
      if (pointer) updatePointerUpData(pointer);
    }
  }, { passive: true });

  window.addEventListener('keydown', function (e) {
    if (e.code === 'KeyP') config.PAUSED = !config.PAUSED;
    if (e.key === ' ') splatStack.push(parseInt(Math.random() * 20) + 5);
  });

  // === Loop ===
  var lastUpdateTime = Date.now();
  var colorUpdateTimer = 0.0;
  function calcDeltaTime () {
    var now = Date.now();
    var dt = (now - lastUpdateTime) / 1000;
    dt = Math.min(dt, 0.016666); lastUpdateTime = now;
    return dt;
  }
  function updateColors (dt) {
    if (!config.COLORFUL) return;
    colorUpdateTimer += dt * config.COLOR_UPDATE_SPEED;
    if (colorUpdateTimer >= 1) {
      colorUpdateTimer = wrap(colorUpdateTimer, 0, 1);
      pointers.forEach(function (p) { p.color = generateColor(); });
    }
  }
  function applyInputs () {
    if (splatStack.length > 0) multipleSplats(splatStack.pop());
    pointers.forEach(function (p) { if (p.moved) { p.moved = false; splatPointer(p); } });
  }
  function step (dt) {
    gl.disable(gl.BLEND);
    gl.viewport(0, 0, velocity.width, velocity.height);

    curlProgram.bind();
    gl.uniform2f(curlProgram.uniforms.texelSize, velocity.texelSizeX, velocity.texelSizeY);
    gl.uniform1i(curlProgram.uniforms.uVelocity, velocity.read.attach(0));
    blit(curl.fbo);

    vorticityProgram.bind();
    gl.uniform2f(vorticityProgram.uniforms.texelSize, velocity.texelSizeX, velocity.texelSizeY);
    gl.uniform1i(vorticityProgram.uniforms.uVelocity, velocity.read.attach(0));
    gl.uniform1i(vorticityProgram.uniforms.uCurl, curl.attach(1));
    gl.uniform1f(vorticityProgram.uniforms.curl, config.CURL);
    gl.uniform1f(vorticityProgram.uniforms.dt, dt);
    blit(velocity.write.fbo);
    velocity.swap();

    divergenceProgram.bind();
    gl.uniform2f(divergenceProgram.uniforms.texelSize, velocity.texelSizeX, velocity.texelSizeY);
    gl.uniform1i(divergenceProgram.uniforms.uVelocity, velocity.read.attach(0));
    blit(divergence.fbo);

    clearProgram.bind();
    gl.uniform1i(clearProgram.uniforms.uTexture, pressure.read.attach(0));
    gl.uniform1f(clearProgram.uniforms.value, config.PRESSURE);
    blit(pressure.write.fbo);
    pressure.swap();

    pressureProgram.bind();
    gl.uniform2f(pressureProgram.uniforms.texelSize, velocity.texelSizeX, velocity.texelSizeY);
    gl.uniform1i(pressureProgram.uniforms.uDivergence, divergence.attach(0));
    for (var i = 0; i < config.PRESSURE_ITERATIONS; i++) {
      gl.uniform1i(pressureProgram.uniforms.uPressure, pressure.read.attach(1));
      blit(pressure.write.fbo);
      pressure.swap();
    }

    gradienSubtractProgram.bind();
    gl.uniform2f(gradienSubtractProgram.uniforms.texelSize, velocity.texelSizeX, velocity.texelSizeY);
    gl.uniform1i(gradienSubtractProgram.uniforms.uPressure, pressure.read.attach(0));
    gl.uniform1i(gradienSubtractProgram.uniforms.uVelocity, velocity.read.attach(1));
    blit(velocity.write.fbo);
    velocity.swap();

    advectionProgram.bind();
    gl.uniform2f(advectionProgram.uniforms.texelSize, velocity.texelSizeX, velocity.texelSizeY);
    var velocityId = velocity.read.attach(0);
    gl.uniform1i(advectionProgram.uniforms.uVelocity, velocityId);
    gl.uniform1i(advectionProgram.uniforms.uSource, velocityId);
    gl.uniform1f(advectionProgram.uniforms.dt, dt);
    gl.uniform1f(advectionProgram.uniforms.dissipation, config.VELOCITY_DISSIPATION);
    blit(velocity.write.fbo);
    velocity.swap();

    gl.viewport(0, 0, dye.width, dye.height);
    gl.uniform1i(advectionProgram.uniforms.uVelocity, velocity.read.attach(0));
    gl.uniform1i(advectionProgram.uniforms.uSource, dye.read.attach(1));
    gl.uniform1f(advectionProgram.uniforms.dissipation, config.DENSITY_DISSIPATION);
    blit(dye.write.fbo);
    dye.swap();
  }
  function renderFrame (target) {
    if (config.BLOOM) applyBloom(dye.read, bloom);
    if (config.SUNRAYS) { applySunrays(dye.read, dye.write, sunrays); blur(sunrays, sunraysTemp, 1); }
    if (target == null || !config.TRANSPARENT) { gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.enable(gl.BLEND); }
    else gl.disable(gl.BLEND);
    var width = target == null ? gl.drawingBufferWidth : target.width;
    var height = target == null ? gl.drawingBufferHeight : target.height;
    gl.viewport(0, 0, width, height);
    var fbo = target == null ? null : target.fbo;
    if (!config.TRANSPARENT) drawColor(fbo, normalizeColor(config.BACK_COLOR));
    if (target == null && config.TRANSPARENT) drawCheckerboard(fbo);
    drawDisplay(fbo, width, height);
  }

  function frame() {
    var dt = calcDeltaTime();
    if (resizeCanvas()) initFramebuffers();
    updateColors(dt);
    applyInputs();
    if (!config.PAUSED) step(dt);
    render(null);
    requestAnimationFrame(frame);
  }

  function boot() {
    resizeCanvas();
    ref = getWebGLContext(canvas);
    if (!ref) return; // sin WebGL, salir silenciosamente
    gl = ref.gl; ext = ref.ext;

    if (isMobile()) { config.DYE_RESOLUTION = 512; }
    if (!ext.supportLinearFiltering) {
      config.DYE_RESOLUTION = 512;
      config.SHADING = false;
      config.BLOOM = false;
      config.SUNRAYS = false;
    }
    buildShaders();
    initProgramsAndFBOs();
    multipleSplats(parseInt(Math.random() * 20) + 5);
    lastUpdateTime = Date.now();
    colorUpdateTimer = 0.0;
    frame();
  }

  // Arranque tras DOM listo (Webflow ya cargado)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();