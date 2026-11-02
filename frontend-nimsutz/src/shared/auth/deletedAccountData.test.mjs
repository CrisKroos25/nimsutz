import assert from 'node:assert/strict';
import test from 'node:test';
import { clearDeletedAccountData } from './deletedAccountData.js';
import { deleteOwnAccount } from '../api/accountApi.js';

function storage(values) {
    const data = new Map(Object.entries(values));
    return { get length() { return data.size; }, key: (index) => [...data.keys()][index],
        getItem: (key) => data.get(key) ?? null, removeItem: (key) => data.delete(key) };
}

test('el borrado limpia preferencias y referencias de pago de la cuenta eliminada', () => {
    const cache = storage({ 'nimsutz.preferredPlanVersion': '2', 'nimsutz.preferredPlanCode': 'basic',
        'payment-attempt:7:quote': 'operation', 'payment-result:7:12': 'quote',
        'payment-attempt:70:quote': 'other-account', 'nimsutz-theme': 'dark' });
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: cache });
    clearDeletedAccountData(7, cache);
    assert.equal(cache.getItem('nimsutz.preferredPlanVersion'), null);
    assert.equal(cache.getItem('nimsutz.preferredPlanCode'), null);
    assert.equal(cache.getItem('payment-attempt:7:quote'), null);
    assert.equal(cache.getItem('payment-result:7:12'), null);
    assert.equal(cache.getItem('payment-attempt:70:quote'), 'other-account');
    assert.equal(cache.getItem('nimsutz-theme'), 'dark');
});

test('el almacenamiento bloqueado no impide terminar el cierre de la sesión', () => {
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true,
        get() { throw new Error('blocked'); } });
    assert.doesNotThrow(() => clearDeletedAccountData(7));
});

test('la API exige DELETE autenticado, CSRF y confirmación explícita sin otro propietario', async () => {
    const original = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (path, options) => {
        calls.push({ path, options });
        return new Response(JSON.stringify(path.endsWith('/session/')
            ? { user: { id: 7 }, csrfToken: 'deletion-csrf' }
            : { user: null, deletion_pending: false }), { status: 200 });
    };
    try {
        assert.deepEqual(await deleteOwnAccount(), { user: null, deletion_pending: false });
        const request = calls.at(-1);
        assert.equal(request.path, '/api/auth/account/');
        assert.equal(request.options.method, 'DELETE');
        assert.equal(request.options.credentials, 'same-origin');
        assert.equal(request.options.headers.get('X-CSRFToken'), 'deletion-csrf');
        assert.deepEqual(JSON.parse(request.options.body), { confirm: true });
    } finally { globalThis.fetch = original; }
});


test('una respuesta incompleta no se presenta como eliminación confirmada', async () => {
    const original = globalThis.fetch;
    try {
        for (const result of [{}, { user: null, deletion_pending: 'false' }]) {
            globalThis.fetch = async () => new Response(JSON.stringify(result), { status: 200 });
            await assert.rejects(deleteOwnAccount(), /No se pudo confirmar/);
        }
    } finally { globalThis.fetch = original; }
});
