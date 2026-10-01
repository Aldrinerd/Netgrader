// static/js/main.js
// Entry point. Loaded as a module from /assets/<version>/js/main.js, so every
// relative import below is versioned too.
import { initLegacyApp } from './legacy/app.js';

// Read by boot-check.js. Runs only if every import above parsed and loaded.
window.__netgraderBooted = true;

initLegacyApp();
