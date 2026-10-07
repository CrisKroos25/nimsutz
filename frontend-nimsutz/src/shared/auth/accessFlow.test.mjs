import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { validateRegistration, passwordRequirements, sessionDestination, readPlanPreference, savePlanPreference, clearPlanPreference, readPlanIntent, savePlanIntent } from './accessFlow.js';
import { getPlans, validateSubscription, registerAccount, serviceMessage } from '../api/accountApi.js';

beforeEach(() => {
    const storage = new Map();
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: {
        getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key),
    } });
});

const values = { name: 'Ana Prueba', email: 'ana@example.test', password: 'test-password', password_confirmation: 'test-password' };
test('registro exige nombre, correo, longitud y confirmación', () => {
    assert.deepEqual(validateRegistration(values), {});
    assert.deepEqual(Object.keys(validateRegistration({ name: ' ', email: 'no-es-correo', password: '1234', password_confirmation: '' })),
        ['name', 'email', 'password', 'password_confirmation']);
    assert.ok(validateRegistration({ ...values, password_confirmation: 'otro-password' }).password_confirmation);
});
test('la navegación solo admite destinos internos conocidos', () => {
    assert.equal(sessionDestination({ next: 'https://externo.test' }), '/files');
    assert.equal(sessionDestination({ next: 'plans' }), '/plans');
    assert.equal(sessionDestination({ next: 'plan_summary' }), '/plans/summary');
    assert.equal(sessionDestination({ user: { role: 'administrador' } }), '/profile');
});
test('requisitos en vivo: longitud y contenido no numérico, sin exigir mayúsculas', () => {
    assert.deepEqual(passwordRequirements('').map((rule) => rule.met), [false, false]);
    assert.deepEqual(passwordRequirements('abc').map((rule) => rule.met), [false, true]);
    assert.deepEqual(passwordRequirements('12345678').map((rule) => rule.met), [true, false]);
    assert.deepEqual(passwordRequirements('１２３４５６７８').map((rule) => rule.met), [true, false]);
    assert.deepEqual(passwordRequirements('una-frase-larga').map((rule) => rule.met), [true, true]);
    assert.ok(validateRegistration({ ...values, password: '12345678', password_confirmation: '12345678' }).password);
    assert.ok(validateRegistration({ ...values, password: 'nueva-clave' }).password_confirmation);
});
test('preferencia sobrevive al login y su limpieza impide pasarla a otra cuenta', () => {
    savePlanPreference('premium-v2');
    assert.equal(readPlanPreference(), 'premium-v2');
    assert.equal(sessionDestination({ next: 'files' }), '/plans/summary');
    clearPlanPreference();
    assert.equal(readPlanPreference(), null);
    assert.equal(sessionDestination({ next: 'files' }), '/files');
});
test('sin acceso al almacenamiento local, sesión y cierre siguen disponibles', () => {
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, get() { throw new Error('bloqueado'); } });
    assert.equal(readPlanPreference(), null);
    assert.doesNotThrow(clearPlanPreference);
    assert.equal(sessionDestination({ next: 'plans' }), '/plans');
});
test('la selección pública no necesita catálogo ni inventa una versión contratada', () => {
    for (const code of ['gratis', 'basico', 'premium']) {
        savePlanIntent(code);
        assert.equal(readPlanIntent(), code);
        assert.equal(readPlanPreference(), null);
        assert.equal(sessionDestination({ next: 'files' }), '/plans/summary');
    }
    savePlanPreference('premium-v2');
    assert.equal(readPlanIntent(), null);
    savePlanIntent('gratis');
    assert.equal(readPlanPreference(), null);
    clearPlanPreference();
    assert.equal(readPlanIntent(), null);
    assert.throws(() => savePlanIntent('un-plan-inexistente'));
});
test('una respuesta incompleta no se confunde con Sin plan activo', () => {
    for (const value of [null, {}, { subscription: 'gratis' }, { subscription: {} }]) assert.throws(() => validateSubscription(value));
    assert.equal(validateSubscription({ subscription: null }), null);
    assert.deepEqual(validateSubscription({ subscription: { plan: { name: 'Gratis' } } }), { plan: { name: 'Gratis' } });
});
test('catálogo exige condiciones válidas del servidor', async () => {
    const original = globalThis.fetch;
    try {
        globalThis.fetch = async () => Response.json({ plans: [{ name: 'Gratis' }] });
        await assert.rejects(getPlans);
        globalThis.fetch = async () => Response.json({ plans: [{ code: 'gratis', version_id: 'g1', name: 'Gratis', price: '0', currency: 'GTQ', capacity_bytes: 104857600, available: true }] });
        assert.equal((await getPlans())[0].version_id, 'g1');
    } finally { globalThis.fetch = original; }
});
test('registro usa CSRF y conserva errores por campo sin fingir éxito', async () => {
    const original = globalThis.fetch;
    const requests = [];
    try {
        globalThis.fetch = async (path, options) => {
            requests.push({ path, options });
            return path.endsWith('/session/') ? Response.json({ csrfToken: 'test-csrf', user: null }) :
                Response.json({ email: ['Este correo ya existe.'] }, { status: 400 });
        };
        await assert.rejects(registerAccount(values), (error) => error.status === 400 && error.fieldErrors.email[0] === 'Este correo ya existe.');
        const request = requests.at(-1);
        assert.equal(request.options.headers.get('X-CSRFToken'), 'test-csrf');
        assert.equal(request.options.credentials, 'same-origin');
        assert.equal(JSON.parse(request.options.body).name, 'Ana Prueba');
    } finally { globalThis.fetch = original; }
});
test('API ausente produce un mensaje de indisponibilidad', () => {
    assert.match(serviceMessage({ status: 404 }, 'El registro'), /no está disponible/);
});
