(function () {
  'use strict';

  var form = document.getElementById('email-form');
  if (!form) return;

  var wrap = form.parentElement; // .form-block
  var doneMsg = wrap.querySelector('.w-form-done');
  var failMsg = wrap.querySelector('.w-form-fail');
  var submitBtn = form.querySelector('[type="submit"]');
  var honeypot = document.getElementById('website');

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    // Campo trampa para bots: si viene lleno, fingimos éxito sin mandar nada.
    if (honeypot && honeypot.value) {
      form.style.display = 'none';
      if (doneMsg) doneMsg.style.display = 'block';
      return;
    }

    var originalLabel = submitBtn ? submitBtn.value : '';
    if (submitBtn) {
      submitBtn.value = submitBtn.getAttribute('data-wait') || 'Enviando...';
      submitBtn.disabled = true;
    }
    if (failMsg) failMsg.style.display = 'none';

    fetch(form.action, { method: 'POST', body: new FormData(form) })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          if (!res.ok || !data || data.ok !== true) throw new Error('submit_failed');
        });
      })
      .then(function () {
        form.style.display = 'none';
        if (doneMsg) doneMsg.style.display = 'block';
      })
      .catch(function () {
        if (failMsg) failMsg.style.display = 'block';
        if (submitBtn) {
          submitBtn.value = originalLabel;
          submitBtn.disabled = false;
        }
      });
  });
})();
