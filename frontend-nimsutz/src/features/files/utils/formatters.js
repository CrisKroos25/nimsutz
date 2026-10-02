/**
 * formatters.js  —  Módulo B (Rodrigo)
 *
 * SRP: Única responsabilidad → formatear valores primitivos para la UI
 *      (bytes → texto legible, ISO date → fecha localizada).
 * OCP: Agregar nuevas unidades o formatos no requiere modificar los consumidores.
 *
 * Nota: estas funciones existían duplicadas en Trash.jsx y FilePages.jsx.
 *       Al extraerlas se elimina la duplicación (DRY) sin tocar los archivos de A.
 */

const BYTE_UNITS = Object.freeze(['B', 'KB', 'MB', 'GB']);

/**
 * Convierte un número de bytes en una cadena legible.
 * Ej.: 1536 → "1.5 KB"
 *
 * @param {number|null|undefined} bytes
 * @returns {string}
 */
export function formatBytes(bytes) {
    const num = Number(bytes);
    if (!num || num <= 0 || !Number.isFinite(num)) return '0 B';
    const exp = Math.min(
        Math.floor(Math.log(num) / Math.log(1024)),
        BYTE_UNITS.length - 1,
    );
    const value = num / 1024 ** exp;
    return `${value.toFixed(exp === 0 ? 0 : 1)} ${BYTE_UNITS[exp]}`;
}

/**
 * Formatea una cadena ISO 8601 como fecha corta en español.
 * Ej.: "2024-06-15T10:30:00Z" → "15 jun 2024"
 *
 * @param {string|null|undefined} isoString
 * @returns {string}
 */
export function formatDate(isoString) {
    if (!isoString) return '—';
    try {
        const d = new Date(isoString);
        if (!Number.isFinite(d.getTime())) return '—';
        return d.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
        });
    } catch {
        return '—';
    }
}
