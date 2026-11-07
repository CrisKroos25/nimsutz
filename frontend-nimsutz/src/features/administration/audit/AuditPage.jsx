import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import Badge from '@shared/components/Badge/Badge';
import Button from '@shared/components/Button/Button';
import Table from '@shared/components/Table/Table';
import { useRemoteData } from '@shared/hooks/useRemoteData';
import { formatDateTime } from '@features/payments/history/historyModel';
import styles from '../AdministrationPages.module.css';
import { getAuditEvent, listAuditEvents } from './auditApi';
import {
    ACTION_LABELS, EMPTY_AUDIT_FILTERS, RESULT_LABELS, RESULT_TONES,
    actionLabel, actorLabel, auditErrorMessage, auditTotalPages, entityLabel,
    hasActiveAuditFilters, metadataRows, resultLabel, validateAuditFilters,
} from './auditModel';

function EventDetail({ eventId, onClose }) {
    const load = useCallback(() => getAuditEvent(eventId), [eventId]);
    const { loading, data, error, reload } = useRemoteData(load);
    const rows = data ? metadataRows(data.metadata) : [];
    return <article className={styles.detail} aria-labelledby="audit-detail-title">
        <h2 id="audit-detail-title">Detalle del evento</h2>
        {loading ? <p role="status">Consultando evento…</p>
            : error ? <div className={styles.alert} role="alert"><p>{auditErrorMessage(error)}</p><Button variant="secondary" onClick={reload}>Reintentar</Button></div>
            : <dl>
                <Row label="Fecha">{formatDateTime(data.created_at)}</Row>
                <Row label="Acción">{actionLabel(data.action)}</Row>
                <Row label="Actor">{actorLabel(data.actor)}</Row>
                <Row label="Entidad">{`${entityLabel(data.entity_type)} · ${data.entity_id}`}</Row>
                <Row label="Resultado">{resultLabel(data.result)}</Row>
                {rows.map((row) => <Row key={row.key} label={row.label}>{row.value}</Row>)}
            </dl>}
        <Button variant="secondary" onClick={onClose}>Cerrar detalle</Button>
    </article>;
}

function Row({ label, children }) { return <div><dt>{label}</dt><dd>{children || '—'}</dd></div>; }

export default function AuditPage() {
    const [draft, setDraft] = useState(EMPTY_AUDIT_FILTERS);
    const [applied, setApplied] = useState(EMPTY_AUDIT_FILTERS);
    const [page, setPage] = useState(1);
    const [selected, setSelected] = useState(null);
    const [problems, setProblems] = useState({});
    const load = useCallback(() => listAuditEvents(applied, page), [applied, page]);
    const { loading, data, error, reload } = useRemoteData(load);

    function change(field, value) { setDraft((current) => ({ ...current, [field]: value })); }
    function submit(event) {
        event.preventDefault();
        const found = validateAuditFilters(draft);
        setProblems(found);
        if (Object.keys(found).length) return;
        setPage(1); setSelected(null); setApplied(draft);
    }
    function clear() { setDraft(EMPTY_AUDIT_FILTERS); setApplied(EMPTY_AUDIT_FILTERS); setProblems({}); setPage(1); setSelected(null); }

    const columns = [
        { key: 'created_at', label: 'Fecha', render: (e) => formatDateTime(e.created_at) },
        { key: 'action', label: 'Acción', render: (e) => actionLabel(e.action) },
        { key: 'actor', label: 'Actor', render: (e) => actorLabel(e.actor) },
        { key: 'entity', label: 'Entidad', render: (e) => `${entityLabel(e.entity_type)} · ${e.entity_id}` },
        { key: 'result', label: 'Resultado', render: (e) => <Badge tone={RESULT_TONES[e.result] || 'neutral'}>{resultLabel(e.result)}</Badge> },
        { key: 'detail', label: 'Detalle', render: (e) => <Button variant="secondary" aria-label={`Ver detalle del evento ${e.id}`} onClick={() => setSelected(e.id)}>Ver detalle</Button> },
    ];

    return <section className={styles.page} aria-labelledby="audit-title">
        <header className={styles.heading}>
            <h1 id="audit-title">Auditoría</h1>
            <p>Registro de solo lectura de cambios administrativos. Los eventos no se pueden editar ni eliminar desde la aplicación.</p>
        </header>
        <form className={styles.filters} onSubmit={submit} aria-label="Filtros de auditoría" noValidate>
            <label>Acción<select value={draft.action} onChange={(e) => change('action', e.target.value)}><option value="">Todas</option>{Object.entries(ACTION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Resultado<select value={draft.result} onChange={(e) => change('result', e.target.value)}><option value="">Todos</option>{Object.entries(RESULT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Tipo de entidad<select value={draft.entity_type} onChange={(e) => change('entity_type', e.target.value)}><option value="">Todas</option><option value="client">Cliente</option><option value="plan">Plan</option><option value="administration">Administración</option></select></label>
            <label>ID de entidad<input value={draft.entity_id} maxLength={64} onChange={(e) => change('entity_id', e.target.value)} /></label>
            <label>ID de administrador<input inputMode="numeric" value={draft.actor_id} aria-invalid={Boolean(problems.actor_id)} aria-describedby={problems.actor_id ? 'audit-actor-error' : undefined} onChange={(e) => change('actor_id', e.target.value)} />{problems.actor_id && <small id="audit-actor-error" role="alert">{problems.actor_id}</small>}</label>
            <label>Desde<input type="date" value={draft.date_from} onChange={(e) => change('date_from', e.target.value)} /></label>
            <label>Hasta<input type="date" value={draft.date_to} aria-invalid={Boolean(problems.date_to)} aria-describedby={problems.date_to ? 'audit-date-error' : undefined} onChange={(e) => change('date_to', e.target.value)} />{problems.date_to && <small id="audit-date-error" role="alert">{problems.date_to}</small>}</label>
            <div className={styles.actions}>
                <Button type="submit" loading={loading} loadingLabel="Consultando…">Aplicar filtros</Button>
                <Button type="button" variant="secondary" disabled={!hasActiveAuditFilters(draft) && !hasActiveAuditFilters(applied)} onClick={clear}>Limpiar</Button>
            </div>
        </form>
        {error && <div className={styles.alert} role="alert"><p>{auditErrorMessage(error)}</p><Button variant="secondary" onClick={reload}>Reintentar</Button></div>}
        <Table caption={data ? `${data.count} eventos` : 'Eventos de auditoría'} columns={columns} rows={data?.results ?? []} loading={loading} rowKey="id" error={error ? 'No se pudo cargar la auditoría.' : undefined} emptyMessage={hasActiveAuditFilters(applied) ? 'No hay eventos que coincidan con los filtros.' : 'Todavía no hay eventos de auditoría.'} />
        {data?.count > 0 && <nav className={styles.pager} aria-label="Paginación de auditoría">
            <Button variant="secondary" disabled={loading || !data.previous} onClick={() => { setSelected(null); setPage((p) => p - 1); }}>Anterior</Button>
            <span role="status">Página {page} de {auditTotalPages(data.count)}</span>
            <Button variant="secondary" disabled={loading || !data.next} onClick={() => { setSelected(null); setPage((p) => p + 1); }}>Siguiente</Button>
        </nav>}
        {selected && <EventDetail key={selected} eventId={selected} onClose={() => setSelected(null)} />}
        <Link to="/administration">Volver al panel</Link>
    </section>;
}
