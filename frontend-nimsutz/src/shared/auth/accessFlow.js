const PREFERENCE_KEY = 'nimsutz.preferredPlanVersion';
const INTENT_KEY = 'nimsutz.preferredPlanCode';
const DESTINATIONS = { files: '/files', plans: '/plans', plan_summary: '/plans/summary', admin: '/profile' };

// Solo valida la forma del código, no que sea uno conocido: el catálogo del servidor
// decide si existe (ver resolvePlanSelection y needsReselection).
const PLAN_CODE_PATTERN = /^[a-z][a-z0-9_-]{0,31}$/;
const isPlanCode = (code) => typeof code === 'string' && PLAN_CODE_PATTERN.test(code);

export function readPlanPreference() {
    try { return sessionStorage.getItem(PREFERENCE_KEY) || null; }
    catch { return null; }
}

export function savePlanPreference(versionId) {
    sessionStorage.setItem(PREFERENCE_KEY, String(versionId));
    sessionStorage.removeItem(INTENT_KEY);
}

// La intención pública se resuelve a una versión del servidor antes de contratar.
export function readPlanIntent() {
    try {
        const code = sessionStorage.getItem(INTENT_KEY);
        return isPlanCode(code) ? code : null;
    } catch { return null; }
}

export function savePlanIntent(code) {
    if (!isPlanCode(code)) throw new Error('El plan seleccionado no es válido.');
    sessionStorage.setItem(INTENT_KEY, code);
    sessionStorage.removeItem(PREFERENCE_KEY);
}

export function clearPlanPreference() {
    try { sessionStorage.removeItem(PREFERENCE_KEY); sessionStorage.removeItem(INTENT_KEY); }
    catch { /* La sesión del servidor se puede cerrar aunque el almacenamiento esté bloqueado. */ }
}

export function sessionDestination(data) {
    if (data?.user?.role === 'administrador') return '/profile';
    // Quien ya tiene suscripción va a sus archivos, aunque quede una selección guardada.
    if (data?.destination === 'files') return '/files';
    if (readPlanPreference() || readPlanIntent()) return '/plans/summary';
    return DESTINATIONS[data?.destination ?? data?.next] || '/files';
}

export function fieldMessage(value) {
    if (Array.isArray(value)) return value.filter((item) => typeof item === 'string').join(' ');
    return typeof value === 'string' ? value : undefined;
}

export function passwordRequirements(password) {
    return [
        { id: 'length', label: 'Al menos ocho caracteres', met: Array.from(password).length >= 8 },
        { id: 'notNumeric', label: 'No contiene únicamente números', met: password.length > 0 && !/^\p{Decimal_Number}+$/u.test(password) },
        { id: 'notWhitespaceOnly', label: 'No contiene únicamente espacios', met: password.trim().length > 0 },
    ];
}

export function validateRegistration(values) {
    const errors = {};
    if (!values.name.trim()) errors.name = 'Ingresa tu nombre completo.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) errors.email = 'Ingresa un correo válido.';
    const requirements = passwordRequirements(values.password);
    if (!requirements[2].met) errors.password = 'La contraseña no puede estar vacía ni contener solo espacios.';
    else if (!requirements[0].met) errors.password = 'Usa al menos ocho caracteres.';
    else if (!requirements[1].met) errors.password = 'La contraseña no puede contener únicamente números.';
    if (!values.password_confirmation) errors.password_confirmation = 'Confirma tu contraseña.';
    else if (values.password !== values.password_confirmation) errors.password_confirmation = 'Las contraseñas no coinciden.';
    return errors;
}

export function resolvePlanSelection(plans, preference, localVersion, intent) {
    const version = localVersion || preference?.preferred_plan_version_id;
    const stale = !localVersion && !intent && preference?.is_current === false;
    const selected = stale ? null : plans.find((plan) => intent
        ? plan.code === intent : String(plan.version_id) === String(version)) || null;
    return { selected, needsReselection: Boolean((version || intent) && !selected) };
}