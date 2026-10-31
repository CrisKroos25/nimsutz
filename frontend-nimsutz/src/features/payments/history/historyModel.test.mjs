import assert from 'node:assert/strict';
import test from 'node:test';
import {
    EMPTY_FILTERS, PAGE_SIZE, buildHistoryQuery, hasActiveFilters, maskedCard, reasonText, totalPages,
    validateFilters, validateHistoryPage, validatePayment, validatePaymentDetail,
} from './historyModel.js';

const payment = (changes = {}) => ({
    id: 7, reference: '5b0f6b7a-0000-4000-8000-000000000001', status: 'approved', reason_code: null,
    operation: 'contract', amount: '15.00', currency: 'GTQ', created_at: '2026-10-27T15:00:00-06:00',
    card_last4: '0001', ...changes,
});

test('la consulta solo lleva los filtros elegidos y el tamaño de página', () => {
    assert.equal(buildHistoryQuery(EMPTY_FILTERS), `?page_size=${PAGE_SIZE}`);
    const query = new URLSearchParams(buildHistoryQuery({ ...EMPTY_FILTERS, status: 'rejected', date_from: '2026-10-01' }, 3));
    assert.equal(query.get('status'), 'rejected');
    assert.equal(query.get('date_from'), '2026-10-01');
    assert.equal(query.get('page'), '3');
    assert.equal(query.has('operation'), false);
    assert.equal(query.has('date_to'), false);
});

test('la página 1 no se envía y nunca se envía un propietario', () => {
    const query = new URLSearchParams(buildHistoryQuery({ ...EMPTY_FILTERS, owner: '5' }, 1));
    assert.equal(query.has('page'), false);
    assert.equal(query.has('owner'), false);
});

test('rango de fechas invertido se detecta antes de consultar', () => {
    assert.deepEqual(validateFilters({ ...EMPTY_FILTERS, date_from: '2026-10-31', date_to: '2026-10-01' }),
        { date_to: 'La fecha final no puede ser anterior a la inicial.' });
    assert.deepEqual(validateFilters({ ...EMPTY_FILTERS, date_from: '2026-10-01', date_to: '2026-10-01' }), {});
    assert.deepEqual(validateFilters(EMPTY_FILTERS), {});
});

test('filtros activos y total de páginas', () => {
    assert.equal(hasActiveFilters(EMPTY_FILTERS), false);
    assert.equal(hasActiveFilters({ ...EMPTY_FILTERS, operation: 'renew' }), true);
    assert.equal(totalPages(0), 1);
    assert.equal(totalPages(PAGE_SIZE), 1);
    assert.equal(totalPages(PAGE_SIZE + 1), 2);
});

test('la tarjeta solo se muestra enmascarada', () => {
    assert.equal(maskedCard('0001'), '•••• 0001');
    for (const value of ['', null, undefined, '12', '1234567890123456']) assert.equal(maskedCard(value), 'No disponible');
});

test('motivo de rechazo conocido y desconocido', () => {
    assert.equal(reasonText('insufficient_funds'), 'Saldo insuficiente');
    assert.equal(reasonText('otro'), 'Motivo no disponible');
});

test('un listado válido pasa y uno incompleto no se interpreta como vacío', () => {
    const empty = { count: 0, next: null, previous: null, results: [] };
    assert.equal(validateHistoryPage(empty), empty);
    assert.equal(validateHistoryPage({ count: 1, next: null, previous: null, results: [payment()] }).count, 1);
    for (const bad of [null, {}, { count: 1 }, { count: -1, results: [] }, { count: 1, results: [payment({ amount: 15 })] },
        { count: 1, results: [payment({ amount: '15' })] }, { count: 1, results: [payment({ status: 'pending' })] },
        { count: 1, results: [payment({ id: '7' })] }]) {
        assert.throws(() => validateHistoryPage(bad));
    }
});

test('el detalle exige líneas con importes de dos decimales y el plan conservado', () => {
    const detail = { ...payment(), lines: [{ code: 'contract_cycle', description: 'Primer ciclo', amount: '15.00' }],
        plan: { plan_code: 'basic', version_id: 2, name: 'Básico', capacity_bytes: 1073741824 } };
    assert.equal(validatePaymentDetail(detail), detail);
    assert.throws(() => validatePaymentDetail({ ...detail, lines: 'x' }));
    assert.throws(() => validatePaymentDetail({ ...detail, lines: [{ code: 'a', description: 'b', amount: 1.5 }] }));
    assert.throws(() => validatePaymentDetail({ ...detail, plan: null }));
    assert.throws(() => validatePayment(null));
});
