// static/js/shell/display-menu.js
// The Display settings popover in the rail. Settings logic lives in
// display-boot.js (window.NetgraderDisplay); this only drives the form.
export function initDisplayMenu(button, panel, display = window.NetgraderDisplay) {
    if (!button || !panel || !display) return;

    const sync = () => {
        const settings = display.load();
        for (const [key, value] of Object.entries(settings)) {
            const input = panel.querySelector(`input[name="${key}"][value="${value}"]`);
            if (input) input.checked = true;
        }
    };
    const open = () => {
        sync();
        panel.hidden = false;
        button.setAttribute('aria-expanded', 'true');
        (panel.querySelector('input:checked') || panel.querySelector('input'))?.focus();
    };
    const close = (returnFocus = true) => {
        panel.hidden = true;
        button.setAttribute('aria-expanded', 'false');
        if (returnFocus) button.focus();
    };

    button.addEventListener('click', () => (panel.hidden ? open() : close()));
    panel.addEventListener('change', (event) => {
        const input = event.target;
        if (!(input instanceof HTMLInputElement) || input.type !== 'radio') return;
        const next = { ...display.load(), [input.name]: input.value };
        display.save(next);
        display.apply(next);
    });
    panel.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { event.stopPropagation(); close(); }
    });
    document.addEventListener('click', (event) => {
        if (!panel.hidden && !panel.contains(event.target) && !button.contains(event.target)) close(false);
    });
}
