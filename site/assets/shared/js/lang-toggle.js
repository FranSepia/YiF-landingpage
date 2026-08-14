(function () {
  var STORAGE_KEY = 'yf-lang';

  function currentLang() {
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) {}
    return saved === 'en' ? 'en' : 'es';
  }

  function applyLang(lang) {
    document.documentElement.setAttribute('lang', lang);

    document.querySelectorAll('[data-en]').forEach(function (el) {
      if (!el.hasAttribute('data-es')) el.setAttribute('data-es', el.innerHTML);
      var next = lang === 'en' ? el.getAttribute('data-en') : el.getAttribute('data-es');
      if (next !== null) el.innerHTML = next;
    });

    document.querySelectorAll('[data-en-placeholder]').forEach(function (el) {
      if (!el.hasAttribute('data-es-placeholder')) el.setAttribute('data-es-placeholder', el.getAttribute('placeholder') || '');
      el.setAttribute('placeholder', (lang === 'en' ? el.getAttribute('data-en-placeholder') : el.getAttribute('data-es-placeholder')) || '');
    });

    document.querySelectorAll('[data-en-value]').forEach(function (el) {
      if (!el.hasAttribute('data-es-value')) el.setAttribute('data-es-value', el.getAttribute('value') || '');
      el.setAttribute('value', (lang === 'en' ? el.getAttribute('data-en-value') : el.getAttribute('data-es-value')) || '');
    });

    var btn = document.querySelector('.lang-toggle-btn');
    if (btn) {
      btn.textContent = lang === 'en' ? 'ES' : 'EN';
      btn.setAttribute('aria-label', lang === 'en' ? 'Cambiar a español' : 'Switch to English');
      btn.setAttribute('title', lang === 'en' ? 'Cambiar a español' : 'Switch to English');
    }

    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) {}

    document.dispatchEvent(new CustomEvent('yf:langchange', { detail: { lang: lang } }));
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyLang(currentLang());
    var btn = document.querySelector('.lang-toggle-btn');
    if (btn) {
      btn.addEventListener('click', function () {
        applyLang(currentLang() === 'en' ? 'es' : 'en');
      });
    }
  });
})();
