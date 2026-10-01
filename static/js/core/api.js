// static/js/core/api.js

// Reads an error body that may not be JSON (a proxy or crash can return HTML).
export async function describeFailure(res, fallback) {
    try {
        const body = await res.json();
        if (body && body.detail) {
            return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
        }
    } catch (e) { /* response was not JSON */ }
    return fallback || `Server error ${res.status} ${res.statusText}`;
}
