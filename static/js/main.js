// static/js/main.js
// Entry point. Loaded as a module from /assets/<version>/js/main.js, so every
// relative import below is versioned too.
import { initLegacyApp } from './legacy/app.js';
import { initDisplayMenu } from './shell/display-menu.js';

// Read by boot-check.js. Runs only if every import above parsed and loaded.
window.__netgraderBooted = true;

// Display menu first, so a legacy failure cannot take it down.
initDisplayMenu(document.getElementById('display-menu-btn'), document.getElementById('display-menu'));
initLegacyApp();
