import { clearPlanPreference } from './accessFlow.js';

export function clearDeletedAccountData(userId, storage) {
    clearPlanPreference();
    try {
        const cache = storage || globalThis.sessionStorage;
        const prefixes = [`payment-attempt:${userId}:`, `payment-result:${userId}:`];
        const keys = Array.from({ length: cache.length }, (_, index) => cache.key(index));
        for (const key of keys) {
            if (prefixes.some((prefix) => key?.startsWith(prefix))) cache.removeItem(key);
        }
    } catch {
        // El borrado del servidor sigue siendo válido aunque el navegador bloquee el almacenamiento.
    }
}
