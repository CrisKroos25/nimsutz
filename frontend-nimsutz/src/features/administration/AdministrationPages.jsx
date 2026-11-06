import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Badge from '@shared/components/Badge/Badge';
import Button from '@shared/components/Button/Button';
import Table from '@shared/components/Table/Table';
import { useRemoteData } from '@shared/hooks/useRemoteData';
import { paymentAmount } from '@features/payments/paymentPresentation';
import { OPERATION_LABELS, STATUS_LABELS, formatDateTime, maskedCard, reasonText, totalPages } from '@features/payments/history/historyModel';
import { getAdministrationPayment, getMetrics, listAdministrationPayments } from './administrationApi';
import styles from './AdministrationPages.module.css';

const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Guatemala' });
const monthStart = `${today.slice(0, 7)}-01`;
const emptyFilters = { client_id: '', status: '', operation: '', date_from: '', date_to: '' };

function Dashboard({ filters }) {
    const load = useCallback(() => getMetrics(filters), [filters]);
    const { loading, data, error, reload } = useRemoteData(load);
    return <section className={styles.page} aria-labelledby="admin-title">
        <header className={styles.heading}><h1 id="admin-title">Administración</h1><p>Resumen actual de cuentas, cobertura y almacenamiento. Los ingresos simulados corresponden al periodo seleccionado.</p></header>
        {error ? <div className={styles.alert} role="alert"><p>{error.message}</p><Button variant="secondary" onClick={reload}>Reintentar</Button></div>
            : loading ? <p role="status">Cargando métricas…</p> : data && <>
                <div className={styles.grid} aria-label="Indicadores administrativos">
                    <Metric label="Clientes" value={data.clients.total} note={`Activas ${data.clients.by_status.activa} · Pendientes ${data.clients.by_status.pendiente_verificacion} · Suspendidas ${data.clients.by_status.suspendida}`} />
                    <Metric label="Suscripciones efectivas activas" value={data.active_subscriptions} />
                    <Metric label="Archivos confirmados" value={data.files.total} note={`${data.files.in_trash} en papelera · Incluidos en consumo`} />
                    <Metric label="Almacenamiento ocupado" value={`${data.storage.used_bytes.toLocaleString('es-GT')} bytes`} note="Incluye papelera; excluye reservas pendientes" />
                    <Metric label="Ingresos simulados aprobados" value={paymentAmount(data.payments.approved_amount, data.payments.currency)} note={`${data.payments.approved_count} aprobados · ${data.payments.rejected_count} rechazados · ${data.period.date_from} a ${data.period.date_to}`} />
                </div>
                <p className={styles.muted}>Cuentas, suscripciones, archivos y consumo son una instantánea al {formatDateTime(data.as_of)}. Solo los pagos usan el periodo seleccionado.</p>
            </>}
        <nav className={styles.links} aria-label="Módulos de administración"><Link to="/administration">Panel de métricas</Link><Link to="/administration/payments">Historial comercial de pagos</Link></nav>
    </section>;
}

function Metric({ label, value, note }) {
    return <article className={styles.metric}><h2>{label}</h2><strong>{value}</strong>{note && <p>{note}</p>}</article>;
}

export function AdministrationDashboardPage() {
    const [filters, setFilters] = useState({ date_from: monthStart, date_to: today });
    const [applied, setApplied] = useState(filters);
    return <><form className={styles.period} onSubmit={(event) => { event.preventDefault(); setApplied(filters); }} aria-label="Periodo de ingresos"><label>Desde <input type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} /></label><label>Hasta <input type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} /></label><Button type="submit">Aplicar periodo</Button></form><Dashboard filters={applied} /></>;
}

function PaymentList() {
    const [draft, setDraft] = useState(emptyFilters);
    const [applied, setApplied] = useState(emptyFilters);
    const [page, setPage] = useState(1);
    const load = useCallback(() => listAdministrationPayments(applied, page), [applied, page]);
    const { loading, data, error, reload } = useRemoteData(load);
    function submit(event) { event.preventDefault(); setPage(1); setApplied(draft); }
    const columns = [
        { key: 'created_at', label: 'Fecha', render: (p) => formatDateTime(p.created_at) },
        { key: 'client', label: 'Cliente', render: (p) => <span>{p.client.name}<br /><small>{p.client.email}</small></span> },
        { key: 'operation', label: 'Operación', render: (p) => OPERATION_LABELS[p.operation] || p.operation },
        { key: 'plan', label: 'Plan contratado', render: (p) => `${p.plan.name || p.plan.plan_code || '—'}${p.plan.version_id ? ` · v${p.plan.version_id}` : ''}` },
        { key: 'amount', label: 'Importe', render: (p) => paymentAmount(p.amount, p.currency) },
        { key: 'card_last4', label: 'Tarjeta', render: (p) => maskedCard(p.card_last4) },
        { key: 'status', label: 'Resultado', render: (p) => <Badge tone={p.status === 'approved' ? 'success' : 'danger'}>{STATUS_LABELS[p.status]}</Badge> },
        { key: 'detail', label: 'Detalle', render: (p) => <Link to={`/administration/payments/${p.id}`}>Ver detalle</Link> },
    ];
    return <section className={styles.page} aria-labelledby="admin-payments-title"><header className={styles.heading}><h1 id="admin-payments-title">Historial comercial</h1><p>Pagos de todas las cuentas. Consulta de solo lectura.</p></header>
        <form className={styles.filters} onSubmit={submit} aria-label="Filtros de pagos">
            <label>Cliente ID<input type="number" min="1" value={draft.client_id} onChange={(event) => setDraft({ ...draft, client_id: event.target.value })} /></label>
            <label>Resultado<select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="">Todos</option><option value="approved">Aprobado</option><option value="rejected">Rechazado</option></select></label>
            <label>Operación<select value={draft.operation} onChange={(event) => setDraft({ ...draft, operation: event.target.value })}><option value="">Todas</option>{Object.entries(OPERATION_LABELS).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label>
            <label>Desde<input type="date" value={draft.date_from} onChange={(event) => setDraft({ ...draft, date_from: event.target.value })} /></label>
            <label>Hasta<input type="date" value={draft.date_to} onChange={(event) => setDraft({ ...draft, date_to: event.target.value })} /></label>
            <div className={styles.actions}><Button type="submit" loading={loading} loadingLabel="Consultando…">Aplicar filtros</Button><Button type="button" variant="secondary" onClick={() => { setDraft(emptyFilters); setApplied(emptyFilters); setPage(1); }}>Limpiar</Button></div>
        </form>
        {error && <div className={styles.alert} role="alert"><p>{error.message}</p><Button variant="secondary" onClick={reload}>Reintentar</Button></div>}
        <Table caption={data ? `${data.count} pagos` : 'Pagos'} columns={columns} rows={data?.results ?? []} loading={loading} rowKey="id" error={error ? 'No se pudo cargar el historial.' : undefined} emptyMessage="No hay pagos que coincidan con los filtros." />
        {data?.count > 0 && <nav className={styles.pager} aria-label="Paginación del historial"><Button variant="secondary" disabled={loading || !data.previous} onClick={() => setPage((p) => p - 1)}>Anterior</Button><span role="status">Página {page} de {totalPages(data.count)}</span><Button variant="secondary" disabled={loading || !data.next} onClick={() => setPage((p) => p + 1)}>Siguiente</Button></nav>}
        <Link to="/administration">Volver al panel</Link>
    </section>;
}

export function AdministrationPaymentsPage() { return <PaymentList />; }

function PaymentDetail({ paymentId }) {
    const load = useCallback(() => getAdministrationPayment(paymentId), [paymentId]);
    const { loading, data, error, reload } = useRemoteData(load);
    return <section className={styles.page} aria-labelledby="admin-payment-detail-title"><header className={styles.heading}><h1 id="admin-payment-detail-title">Detalle administrativo del pago</h1><p>Registro histórico de solo lectura; la tarjeta muestra únicamente los últimos cuatro dígitos.</p></header>
        {loading ? <p role="status">Consultando pago…</p> : error ? <div className={styles.alert} role="alert"><p>{error.message}</p><Button variant="secondary" onClick={reload}>Reintentar</Button></div> : data && <article className={styles.detail}><h2>{paymentAmount(data.amount, data.currency)} · {STATUS_LABELS[data.status]}</h2><dl><Row label="Cliente">{data.client.name} · {data.client.email} (ID {data.client.id})</Row><Row label="Operación">{OPERATION_LABELS[data.operation]}</Row><Row label="Referencia">{data.reference}</Row><Row label="Plan contratado">{data.plan.name || data.plan.plan_code} · versión {data.plan.version_id}</Row><Row label="Tarjeta">{maskedCard(data.card_last4)}</Row><Row label="Fecha">{formatDateTime(data.created_at)}</Row><Row label="Motivo">{reasonText(data.reason_code)}</Row></dl><h3>Conceptos</h3><ul>{data.lines.map((line, index) => <li key={`${line.code}-${index}`}>{line.description}<strong>{paymentAmount(line.amount, data.currency)}</strong></li>)}</ul></article>}
        <Link to="/administration/payments">Volver al historial</Link></section>;
}

function Row({ label, children }) { return <div><dt>{label}</dt><dd>{children || '—'}</dd></div>; }
export function AdministrationPaymentDetailPage() { const { paymentId } = useParams(); return <PaymentDetail key={paymentId} paymentId={paymentId} />; }
