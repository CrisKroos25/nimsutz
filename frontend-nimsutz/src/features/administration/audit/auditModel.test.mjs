import assert from 'node:assert/strict';
import test from 'node:test';
import {
    actorLabel, buildAuditQuery, metadataRows, validateAuditFilters, validateAuditPage,
} from './auditModel.js';

test('la consulta omite filtros vacíos y fija la paginación', () => {
    assert.equal(buildAuditQuery({ action: '', result: 'rejected' }, 2), '?result=rejected&page=2&page_size=20');
});

test('valida administrador y rango de fechas', () => {
    assert.ok(validateAuditFilters({ actor_id: 'abc' }).actor_id);
    assert.ok(validateAuditFilters({ date_from: '2026-11-05', date_to: '2026-11-01' }).date_to);
    assert.deepEqual(validateAuditFilters({ actor_id: '3', date_from: '2026-11-01', date_to: '2026-11-01' }), {});
});

test('la metadata solo muestra claves del contrato', () => {
    const rows = metadataRows({ new_status: 'suspendida', previous_active: true, password: 'secreto' });
    assert.deepEqual(rows.map((r) => r.key), ['new_status', 'previous_active']);
    assert.equal(rows[1].value, 'Sí');
});

test('actor ausente se describe sin inventar datos', () => {
    assert.equal(actorLabel(null), 'Sistema o cuenta eliminada');
    assert.equal(actorLabel({ id: 4, label: 'a@x.test' }), 'a@x.test');
});

test('rechaza respuestas con forma inesperada', () => {
    assert.throws(() => validateAuditPage({ count: 'x' }));
    assert.equal(validateAuditPage({ count: 0, results: [] }).count, 0);
});
