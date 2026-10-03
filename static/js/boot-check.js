// static/js/boot-check.js
// Classic ES5 script. Shows the unsupported-browser notice when the app never
// started: either the browser cannot run ES modules at all, or it runs them
// but cannot parse the app's code. main.js sets the flag once its imports
// have loaded, so a parse failure anywhere in the module graph leaves it unset.
window.addEventListener('load', function () {
    if (window.__netgraderBooted) { return; }
    var notice = document.getElementById('unsupported-browser');
    if (notice) { notice.hidden = false; }
});
