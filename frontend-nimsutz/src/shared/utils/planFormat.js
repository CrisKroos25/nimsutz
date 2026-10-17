// @shared/utils/format.js
export function formatStorage(bytes) {
    const num = Number(bytes);
    if (!Number.isFinite(num) || num <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const exponent = Math.max(0, Math.min(Math.floor(Math.log(num) / Math.log(1024)), units.length - 1));
    const value = num / 1024 ** exponent;
    // Number(...) quita el decimal sobrante: 100 MB en vez de 100.0 MB.
    return `${Number(value.toFixed(exponent === 0 ? 0 : 1))} ${units[exponent]}`;
}

export function formatDate(isoString) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
}

export const formatPrice = (price) => Number(price);