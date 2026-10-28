import assert from 'node:assert/strict';
import test from 'node:test';
import {
    changeTargets, coverageEnd, isExpired, isFree, nextStep, quoteErrorMessage, quotaState,
    validateCurrent, validateQuote,
} from './subscriptionModel.js';

const sub = (code = 'basic', changes = {}) => ({ id: 1, status: 'active', started_at: '2026-10-01T00:00:00-06:00',
    expires_at: '2026-11-01T00:00:00-06:00', coverage_end: '2026-11-01T00:00:00-06:00', cycle_anchor_day: 1,
    plan: { plan_code: code, version_id: code === 'free' ? 1 : 2, name: code, capacity_bytes: 1073741824 }, ...changes });
const current = (changes = {}) => ({ subscription: sub(), next_cycle: null, scheduled_change: null, allowed_actions: ['change', 'renew'], ...changes });
const quote = (changes = {}) => ({ quote: { id: 'a1', operation: 'renew', expires_at: '2026-10-27T22:00:00-06:00', currency: 'GTQ',
    total: '15.00', requires_payment: true, plan: { plan_code: 'basic', version_id: 2, name: 'Básico', capacity_bytes: 1 },
    lines: [{ code: 'renewal_cycle', description: 'Renovación', amount: '15.00' }],
    effect: { kind: 'renew', starts_at: null, ends_at: null, scheduled_change_at: null }, ...changes } });

test('estado actual válido con y sin suscripción', () => {
    const ok = validateCurrent(current({ next_cycle: { starts_at: 'x', ends_at: 'y', plan_version_id: 2 } }));
    assert.deepEqual(ok.allowed, ['change', 'renew']);
    assert.equal(ok.nextCycle.plan_version_id, 2);
    assert.equal(validateCurrent({ subscription: null, next_cycle: null, scheduled_change: null, allowed_actions: ['contract'] }).subscription, null);
});

test('un estado incompleto o con acciones desconocidas no se interpreta como válido', () => {
    for (const bad of [null, {}, { subscription: null }, current({ allowed_actions: 'renew' }), current({ allowed_actions: ['regalar'] }),
        current({ scheduled_change: { id: 1 } }), current({ next_cycle: 'x' })]) assert.throws(() => validateCurrent(bad));
});

test('Gratis no muestra fin de cobertura y un plan pagado sí', () => {
    assert.equal(isFree(sub('free')), true);
    assert.equal(coverageEnd(sub('free')), null);
    assert.equal(coverageEnd(sub('basic')), '2026-11-01T00:00:00-06:00');
    assert.equal(coverageEnd(sub('basic', { coverage_end: null })), '2026-11-01T00:00:00-06:00');
    assert.equal(coverageEnd(null), null);
});

test('la cotización exige importes como cadena de dos decimales y efecto conocido', () => {
    assert.equal(validateQuote(quote()).total, '15.00');
    for (const bad of [null, {}, quote({ total: 15 }), quote({ total: '15' }), quote({ effect: { kind: 'regalo' } }),
        quote({ lines: [{ description: 'x', amount: 1 }] }), quote({ requires_payment: 'si' }), quote({ operation: 'borrar' })]) {
        assert.throws(() => validateQuote(bad));
    }
});

test('siguiente paso: pagar, confirmar sin cobro, o nada; un total 0.00 de mejora sigue yendo al pago', () => {
    assert.equal(nextStep(validateQuote(quote())), 'checkout');
    assert.equal(nextStep(validateQuote(quote({ total: '0.00', requires_payment: true, effect: { kind: 'upgrade' } }))), 'checkout');
    assert.equal(nextStep(validateQuote(quote({ total: '0.00', requires_payment: false, effect: { kind: 'schedule_downgrade' } }))), 'confirm');
    assert.equal(nextStep(validateQuote(quote({ total: '0.00', requires_payment: false, effect: { kind: 'schedule_free' } }))), 'confirm');
    assert.equal(nextStep(validateQuote(quote({ requires_payment: false, effect: { kind: 'activate' } }))), 'none');
});

test('vigencia de la cotización', () => {
    const q = validateQuote(quote());
    assert.equal(isExpired(q, Date.parse('2026-10-27T21:59:59-06:00')), false);
    assert.equal(isExpired(q, Date.parse('2026-10-27T22:00:00-06:00')), true);
});

test('cambio de plan: no se ofrece el actual y los no contratables quedan deshabilitados', () => {
    const plans = [{ plan_code: 'free', version_id: 1, available: true }, { plan_code: 'basic', version_id: 2, available: true },
        { plan_code: 'premium', version_id: 3, available: false }];
    const targets = changeTargets(plans, sub('basic'));
    assert.deepEqual(targets.map((t) => [t.plan.plan_code, t.selectable]), [['free', true], ['premium', false]]);
    assert.equal(changeTargets(plans, null).length, 3);
});

test('exceso de cuota y consumo', () => {
    assert.deepEqual(quotaState({ used_bytes: 50, capacity_bytes: 100 }), { exceeded: false, percent: 50, available: 50 });
    assert.deepEqual(quotaState({ used_bytes: 150, capacity_bytes: 100 }), { exceeded: true, percent: 150, available: 0 });
    assert.equal(quotaState(null), null);
});

test('mensajes de error por código del contrato', () => {
    assert.match(quoteErrorMessage({ code: 'renewal_limit_reached' }), /ciclo siguiente/);
    assert.equal(quoteErrorMessage({ code: 'quota_exceeded', message: 'Tu consumo excede' }), 'Tu consumo excede');
    assert.equal(quoteErrorMessage({ code: 'otro', message: 'Detalle del servidor' }), 'Detalle del servidor');
    assert.match(quoteErrorMessage(null), /No se pudo/);
});
