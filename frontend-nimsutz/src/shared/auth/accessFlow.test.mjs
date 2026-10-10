import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { resolvePlanSelection, validateRegistration, passwordRequirements, sessionDestination, readPlanPreference, savePlanPreference, clearPlanPreference, readPlanIntent, savePlanIntent } from './accessFlow.js';
import { getPlans, getPreference, setPreference, selectPlan, getAccountOverview, withAccountDestination, validateSubscription, registerAccount, serviceMessage } from '../api/accountApi.js';

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
        globalThis.fetch = async () => Response.json({ plans: [{ plan_code: 'free', version_id: 'g1', name: 'Gratis', price: '0', currency: 'GTQ', capacity_bytes: 104857600, contractable: true }] });
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


test('preferencia usa el contrato real y conserva versiones desactualizadas', async () => {
    const original = globalThis.fetch;
    try {
        globalThis.fetch = async (path, options) => {
            if (path.endsWith('/session/')) return Response.json({ csrfToken: 'test-csrf' });
            if (options.method === 'PUT') assert.deepEqual(JSON.parse(options.body), { plan_version_id: 3 });
            return Response.json({ preference: { version_id: 3, is_current: false } });
        };
        assert.deepEqual(await getPreference(), { preferred_plan_version_id: 3, is_current: false });
        await setPreference(3);
        globalThis.fetch = async () => Response.json({});
        await assert.rejects(getPreference);
    } finally { globalThis.fetch = original; }
});

test('perfil distingue cobertura ausente, nula y activa usando usage real', async () => {
    const original = globalThis.fetch;
    try {
        globalThis.fetch = async () => Response.json({ coverage: null, usage: { used_bytes: 0, capacity_bytes: 0 }, destination: 'plans' });
        assert.equal((await getAccountOverview()).subscription, null);
        const session = { user: { id: 1, role: 'cliente' } };
        assert.equal(sessionDestination(await withAccountDestination(session)), '/plans');
        globalThis.fetch = async () => Response.json({ coverage: { plan: { name: 'Gratis' } }, usage: { used_bytes: 512, capacity_bytes: 104857600 }, destination: 'files' });
        const overview = await getAccountOverview();
        assert.equal(overview.subscription.plan.name, 'Gratis');
        assert.equal(overview.storage.used_bytes, 512);
        assert.equal(sessionDestination(await withAccountDestination(session)), '/files');
        globalThis.fetch = async () => Response.json({ usage: {} });
        await assert.rejects(getAccountOverview);
        const failedAccess = await withAccountDestination(session);
        assert.deepEqual(failedAccess.user, session.user);
        assert.equal(failedAccess.destination, 'plans');
        assert.ok(failedAccess.accessError);
        assert.deepEqual(await withAccountDestination({ user: null }), { user: null });
    } finally { globalThis.fetch = original; }
});


test('una preferencia no bloquea archivos cuando el servidor confirma cobertura', () => {
    savePlanIntent('premium');
    assert.equal(sessionDestination({ destination: 'files' }), '/files');
    assert.equal(sessionDestination({ destination: 'plans' }), '/plans/summary');
});


test('selección conserva la preferencia del servidor al entrar desde otra pestaña', () => {
    const plans = [{ code: 'gratis', version_id: 1 }, { code: 'premium', version_id: 3 }];
    assert.deepEqual(resolvePlanSelection(plans, { preferred_plan_version_id: 3, is_current: true }, null, null),
        { selected: plans[1], needsReselection: false });
    assert.equal(resolvePlanSelection(plans, { preferred_plan_version_id: 3 }, null, 'gratis').selected, plans[0]);
    assert.equal(resolvePlanSelection(plans, { preferred_plan_version_id: 3 }, '1', null).selected, plans[0]);
});

test('plan ausente o versión desactualizada exige elegir de nuevo, sin reemplazo silencioso', () => {
    const plans = [{ code: 'gratis', version_id: 2 }];
    assert.deepEqual(resolvePlanSelection(plans, { preferred_plan_version_id: 1, is_current: false }, null, null),
        { selected: null, needsReselection: true });
    assert.equal(resolvePlanSelection(plans, { preferred_plan_version_id: 1 }, '1', null).needsReselection, true);
    assert.equal(resolvePlanSelection(plans, { preferred_plan_version_id: null }, null, 'premium').needsReselection, true);
    assert.deepEqual(resolvePlanSelection(plans, { preferred_plan_version_id: null }, null, null),
        { selected: null, needsReselection: false });
});

test('fallo al guardar selección no borra intención ni la convierte en cobertura', async () => {
    const original = globalThis.fetch;
    savePlanIntent('premium');
    try {
        globalThis.fetch = async (path) => path.endsWith('/session/')
            ? Response.json({ csrfToken: 'test-csrf' })
            : Response.json({ code: 'plan_conditions_changed', detail: 'Vuelve a elegir.' }, { status: 400 });
        await assert.rejects(setPreference(3), (error) => error.code === 'plan_conditions_changed');
        assert.equal(readPlanIntent(), 'premium');
        assert.equal(readPlanPreference(), null);
    } finally { globalThis.fetch = original; }
});


test('fallo de cobertura conserva identidad y reintento recupera acceso sin otro login', async () => {
    const original = globalThis.fetch;
    const session = { user: { id: 42, role: 'cliente' }, csrfToken: 'csrf-test' };
    const paths = [];
    try {
        globalThis.fetch = async (path) => { paths.push(path); return Response.json({}, { status: 503 }); };
        const failed = await withAccountDestination(session);
        assert.equal(failed.user, session.user);
        assert.equal(failed.csrfToken, session.csrfToken);
        assert.ok(failed.accessError);
        globalThis.fetch = async (path) => {
            paths.push(path);
            return Response.json({ coverage: { plan: { name: 'Gratis' } }, destination: 'files' });
        };
        const recovered = await withAccountDestination(session);
        assert.equal(recovered.destination, 'files');
        assert.equal(recovered.accessError, undefined);
        assert.ok(paths.every((path) => path === '/api/account/overview/'));
    } finally { globalThis.fetch = original; }
});

test('rechazo de versión recarga catálogo sin aceptar automáticamente la nueva', async () => {
    const original = globalThis.fetch;
    const requests = [];
    try {
        globalThis.fetch = async (path, options) => {
            requests.push({ path, method: options.method });
            if (path.endsWith('/session/')) return Response.json({ csrfToken: 'csrf-test' });
            if (options.method === 'PUT') return Response.json({ code: 'plan_conditions_changed' }, { status: 409 });
            return Response.json({ plans: [{ plan_code: 'free', version_id: 2, name: 'Gratis', price: '0', currency: 'GTQ', capacity_bytes: 104857600, contractable: true }] });
        };
        const result = await selectPlan(1);
        assert.equal(result.needsReselection, true);
        assert.equal(result.plans[0].version_id, 2);
        assert.equal(requests.filter((request) => request.method === 'PUT').length, 1);
        assert.ok(!requests.some((request) => request.path.includes('activate-free')));
        globalThis.fetch = async () => Response.json({}, { status: 503 });
        await assert.rejects(selectPlan(1));
    } finally { globalThis.fetch = original; }
});
