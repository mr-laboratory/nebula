// Applies the saved theme before first paint so pages never flash the wrong colors.
// A file (not an inline script) so a strict Content-Security-Policy can allow it as 'self'.
;(function () {
  var mode = 'system'
  try {
    mode = localStorage.getItem('nebula:theme') || 'system'
  } catch {
    // storage blocked: follow the system setting
  }
  if (mode !== 'light' && mode !== 'dark') {
    mode = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  document.documentElement.dataset.mode = mode
  document.documentElement.style.colorScheme = mode
})()
