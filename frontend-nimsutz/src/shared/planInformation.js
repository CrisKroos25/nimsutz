// Respaldo para cuando el backend no responde. Solo informativo: no concede cobertura
// ni sustituye al catálogo versionado.
export const FALLBACK_PLANS = [
    { code: 'gratis',  name: 'Gratis',  price: 0,  currency: 'GTQ', capacity_bytes: 100 * 1024 ** 2,  available: false },
    { code: 'basico',  name: 'Básico',  price: 15, currency: 'GTQ', capacity_bytes: 1024 ** 3,        available: false },
    { code: 'premium', name: 'Premium', price: 30, currency: 'GTQ', capacity_bytes: 5 * 1024 ** 3,    available: false },
];