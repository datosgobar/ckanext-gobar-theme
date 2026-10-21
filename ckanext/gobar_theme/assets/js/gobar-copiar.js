/**
 * gobar-copiar.js
 * Botones [data-gobar-copiar="<texto>"]: copian el texto al portapapeles y
 * muestran la confirmación de data-copiado unos segundos.
 */
document.addEventListener('click', function (e) {
  var btn = e.target.closest('[data-gobar-copiar]');
  if (!btn) return;
  var texto = btn.getAttribute('data-gobar-copiar');
  var label = btn.querySelector('.gobar-copiar-label');
  var original = label.textContent;

  function ok() {
    btn.classList.add('is-copiado');
    label.textContent = btn.getAttribute('data-copiado');
    setTimeout(function () {
      btn.classList.remove('is-copiado');
      label.textContent = original;
    }, 2000);
  }

  // navigator.clipboard solo existe en contextos seguros (https/localhost);
  // si no está o falla, se copia con un textarea temporal.
  function fallback() {
    var t = document.createElement('textarea');
    t.value = texto;
    t.setAttribute('readonly', '');
    t.style.position = 'fixed';
    t.style.opacity = '0';
    document.body.appendChild(t);
    t.select();
    try { if (document.execCommand('copy')) ok(); } catch (err) { /* sin portapapeles */ }
    document.body.removeChild(t);
  }

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(texto).then(ok, fallback);
  } else {
    fallback();
  }
});
