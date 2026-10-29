import assert from 'node:assert/strict';
import test from 'node:test';
import { createPaymentAttempt } from './paymentAttempt.js';

const body = { quote_id: 'quote', card: { number: '9999000000000001', security_code: '123' } };
const result = { payment: { id: 1, status: 'approved' } };
function setup(overrides = {}) {
    const values = new Map();
    const calls = [];
    const storage = { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
    const options = {
        storage, scope: 'customer:quote', uuid: () => 'operation-key',
        send: async (key, request) => { calls.push({ key, request }); return result; },
        lookup: async () => result,
        ...overrides,
    };
    return { attempt: createPaymentAttempt(options), values, calls, options };
}

test('double click sends a single operation', async () => {
    let finish;
    let count = 0;
    const { attempt } = setup({ send: () => { count++; return new Promise(resolve => { finish = resolve; }); } });
    const first = attempt.submit(body);
    assert.equal(await attempt.submit(body), null);
    finish(result);
    assert.deepEqual(await first, result);
    assert.equal(count, 1);
});

test('lost response retains only key and retries the original body', async () => {
    let count = 0;
    const requests = [];
    const { attempt, values } = setup({ send: async (key, request) => {
        requests.push({ key, request });
        if (++count === 1) throw new TypeError('network');
        return result;
    } });
    await assert.rejects(attempt.submit(body));
    assert.deepEqual([...values.values()], ['operation-key']);
    assert.equal(JSON.stringify([...values]).includes('123'), false);
    await attempt.submit({ ...body, card: { security_code: '999' } });
    assert.deepEqual(requests[0], requests[1]);
    assert.equal(values.size, 0);
});

test('reload recovers persisted operation without saving card data', async () => {
    const { attempt, options } = setup({ send: async () => { throw new TypeError('network'); } });
    await assert.rejects(attempt.submit(body));
    const reloaded = createPaymentAttempt(options);
    assert.equal(reloaded.hasRequest, false);
    assert.equal(reloaded.key, 'operation-key');
    assert.deepEqual(await reloaded.recover(), result);
    assert.equal(reloaded.key, null);
});

test('404 recovery never permits a new key', async () => {
    const { attempt, options } = setup({
        send: async () => { throw new TypeError('network'); },
        lookup: async () => { throw Object.assign(new Error('pending'), { status: 404 }); },
    });
    await assert.rejects(attempt.submit(body));
    const reloaded = createPaymentAttempt(options);
    await assert.rejects(reloaded.recover());
    assert.equal(reloaded.key, 'operation-key');
});

test('initial invalid request permits correction; uncertain request preserves key', async () => {
    const error = Object.assign(new Error('invalid'), { status: 400, code: 'invalid_request' });
    const { attempt, options } = setup({ send: async () => { throw error; } });
    await assert.rejects(attempt.submit(body));
    assert.equal(attempt.key, null);
    options.storage.setItem('payment-attempt:customer:quote', 'old-key');
    const reloaded = createPaymentAttempt(options);
    await assert.rejects(reloaded.submit(body));
    assert.equal(reloaded.key, 'old-key');
});

test('processed rejection clears key so voluntary retry uses a new operation', async () => {
    let generated = 0;
    const { attempt, calls } = setup({ uuid: () => String(++generated), send: async (key) => {
        calls.push(key);
        return { payment: { id: generated, status: 'rejected' } };
    } });
    await attempt.submit(body);
    await attempt.submit(body);
    assert.deepEqual(calls, ['1', '2']);
});

test('unavailable session storage prevents sending a nonrecoverable charge', async () => {
    let count = 0;
    const { attempt } = setup({
        storage: { getItem: () => null, setItem: () => { throw new Error('blocked'); } },
        send: async () => { count++; return result; },
    });
    await assert.rejects(attempt.submit(body));
    await assert.rejects(attempt.submit(body));
    assert.equal(count, 0);
});
