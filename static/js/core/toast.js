// static/js/core/toast.js
import { icon } from './icons.js';

// Text only: some messages carry a student's filename.
export function showToast(container, msg, duration = 3000) {
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    const text = document.createElement('span');
    text.textContent = msg;
    toast.append(icon('info'), text);
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
    }, duration);
}
