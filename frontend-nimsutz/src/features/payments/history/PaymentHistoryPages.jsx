import { useCallback, useId, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../../shared/auth/AuthContext';
import Badge from '../../../shared/components/Badge/Badge';
import Button from '../../../shared/components/Button/Button';
import Table from '../../../shared/components/Table/Table';
import { useRemoteData } from '../../../shared/hooks/useRemoteData';
import { paymentAmount } from '../paymentPresentation';
import { getPaymentDetail, listPayments } from './historyApi';
import {
    EMPTY_FILTERS, OPERATION_LABELS, STATUS_LABELS, formatDateTime, hasActiveFilters, historyErrorMessage,
    maskedCard, reasonText, totalPages, validateFilters,
} from './historyModel';
import styles from './PaymentHistoryPages.module.css';

const statusBadge = (payment) => <Badge tone={payment.status === 'approved' ? 'success' : 'danger'}>
    {STATUS_LABELS[payment.status]}
</Badge>;

function SelectField({ name, label, value, onChange, options, error }) {
    const id = useId();
    return <div className={styles.field}>
        <label htmlFor={id}>{label}</label>
        <select id={id} name={name} value={value} onChange={(event) => onChange(event.target.value)} aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined}>
            <option value="">Todos</option>
            {Object.entries(options).map(([code, text]) => <option key={code} value={code}>{text}</option>)}
        </select>
        {error && <p id={`${id}-error`} role="alert" className={styles.fieldError}>{error}</p>}
    </div>;
}

function DateField({ name, label, value, onChange, error }) {
    const id = useId();
    return <div className={styles.field}>
        <label htmlFor={id}>{label}</label>
        <input id={id} name={name} type="date" value={value} onChange={(event) => onChange(event.target.value)}
            aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined} />
        {error && <p id={`${id}-error`} role="alert" className={styles.fieldError}>{error}</p>}
    </div>;
}

function History() {
    const [draft, setDraft] = useState(EMPTY_FILTERS);
    const [applied, setApplied] = useState(EMPTY_FILTERS);
    const [page, setPage] = useState(1);
    const [localErrors, setLocalErrors] = useState({});

    const load = useCallback(() => listPayments(applied, page), [applied, page]);
    const { loading, data, error, reload } = useRemoteData(load);
    const serverErrors = error?.status === 400 ? error.fieldErrors || {} : {};
    const fieldError = (name) => localErrors[name] || [].concat(serverErrors[name] || [])[0];

    function submit(event) {
        event.preventDefault();
        const errors = validateFilters(draft);
        setLocalErrors(errors);
        if (Object.keys(errors).length) {
            event.currentTarget.elements.namedItem(Object.keys(errors)[0])?.focus();
            return;
        }
        setPage(1);
        setApplied(draft);
    }

    function clear() {
        setDraft(EMPTY_FILTERS);
        setLocalErrors({});
        setPage(1);
        setApplied(EMPTY_FILTERS);
    }

    const filtered = hasActiveFilters(applied);
    const rows = data?.results ?? [];
    const pages = data ? totalPages(data.count) : 1;
    const columns = [
        { key: 'created_at', label: 'Fecha', render: (p) => formatDateTime(p.created_at) },
        { key: 'operation', label: 'Concepto', render: (p) => OPERATION_LABELS[p.operation] },
        { key: 'reference', label: 'Referencia', render: (p) => <span className={styles.reference} title={p.reference}>{p.reference.slice(0, 8)}</span> },
        { key: 'amount', label: 'Importe', render: (p) => paymentAmount(p.amount, p.currency) },
        { key: 'card_last4', label: 'Tarjeta', render: (p) => maskedCard(p.card_last4) },
        { key: 'status', label: 'Resultado', render: statusBadge },
        { key: 'detail', label: 'Detalle', render: (p) => <Link to={`/payments/history/${p.id}`}
            aria-label={`Ver detalle del pago del ${formatDateTime(p.created_at)}`}>Ver detalle</Link> },
    ];

    return <section className={styles.page} aria-labelledby="history-title">
        <header className={styles.heading}>
            <h1 id="history-title">Historial de pagos</h1>
            <p>Consulta los pagos aprobados y rechazados de tu cuenta. Es un registro de solo lectura.</p>
        </header>

        <form className={`${styles.card} ${styles.filters}`} onSubmit={submit} aria-label="Filtros del historial" noValidate>
            <SelectField name="status" label="Resultado" value={draft.status} options={STATUS_LABELS} error={fieldError('status')}
                onChange={(status) => setDraft({ ...draft, status })} />
            <SelectField name="operation" label="Concepto" value={draft.operation} options={OPERATION_LABELS} error={fieldError('operation')}
                onChange={(operation) => setDraft({ ...draft, operation })} />
            <DateField name="date_from" label="Desde" value={draft.date_from} error={fieldError('date_from')}
                onChange={(date_from) => setDraft({ ...draft, date_from })} />
            <DateField name="date_to" label="Hasta" value={draft.date_to} error={fieldError('date_to')}
                onChange={(date_to) => setDraft({ ...draft, date_to })} />
            <div className={styles.filterActions}>
                <Button type="submit" loading={loading} loadingLabel="Consultando…">Aplicar filtros</Button>
                <Button type="button" variant="secondary" onClick={clear} disabled={loading && !filtered && !hasActiveFilters(draft)}>
                    Limpiar
                </Button>
            </div>
        </form>

        {error && error.status !== 400 && <div className={styles.alert} role="alert">
            <p>{historyErrorMessage(error)}</p>
            <Button variant="secondary" onClick={reload}>Reintentar</Button>
        </div>}

        <Table caption={data ? `${data.count} pago${data.count === 1 ? '' : 's'}${filtered ? ' con los filtros aplicados' : ''}` : 'Pagos'}
            columns={columns} rows={rows} loading={loading} rowKey="id"
            error={error ? (error.status === 400 ? 'Corrige los filtros para ver el historial.' : 'No se pudo cargar el historial.') : undefined}
            emptyMessage={filtered ? 'No hay pagos que coincidan con los filtros.'
                : 'Todavía no tienes pagos. Cuando contrates o renueves un plan aparecerán aquí.'} />

        {data && data.count > 0 && <nav className={styles.pager} aria-label="Paginación del historial">
            <Button variant="secondary" disabled={loading || !data.previous} onClick={() => setPage((value) => value - 1)}>Anterior</Button>
            <span role="status">Página {page} de {pages}</span>
            <Button variant="secondary" disabled={loading || !data.next} onClick={() => setPage((value) => value + 1)}>Siguiente</Button>
        </nav>}
        <Link to="/subscription">Volver a mi suscripción</Link>
    </section>;
}

export function PaymentHistoryPage() {
    const { user } = useAuth();
    // Si cambia la cuenta de la sesión, el estado de filtros y páginas empieza de cero.
    return <History key={user.id} />;
}

function Row({ label, children }) {
    return <div className={styles.detailRow}><dt>{label}</dt><dd>{children}</dd></div>;
}

function Detail({ paymentId }) {
    const load = useCallback(() => getPaymentDetail(paymentId), [paymentId]);
    const { loading, data: payment, error, reload } = useRemoteData(load);
    const rejected = payment?.status === 'rejected';
    return <section className={styles.page} aria-labelledby="payment-detail-title">
        <header className={styles.heading}>
            <h1 id="payment-detail-title">Detalle del pago</h1>
            <p>Registro de solo lectura. Por seguridad no se muestra el número completo de la tarjeta.</p>
        </header>
        {loading ? <p role="status">Consultando el pago…</p> : error ? <div className={styles.alert} role="alert">
            <p>{historyErrorMessage(error)}</p>
            {error.status !== 404 && <Button variant="secondary" onClick={reload}>Reintentar</Button>}
        </div> : <article className={styles.card}>
            <div className={styles.detailHead}>
                <h2>{paymentAmount(payment.amount, payment.currency)}</h2>
                {statusBadge(payment)}
            </div>
            <dl className={styles.details}>
                <Row label="Concepto">{OPERATION_LABELS[payment.operation]}</Row>
                <Row label="Fecha">{formatDateTime(payment.created_at)}</Row>
                <Row label="Referencia"><span className={styles.reference}>{payment.reference}</span></Row>
                <Row label="Tarjeta">{maskedCard(payment.card_last4)}</Row>
                <Row label="Moneda">{payment.currency}</Row>
                <Row label="Plan">{payment.plan.name ? `${payment.plan.name}${payment.plan.version_id ? ` (versión ${payment.plan.version_id})` : ''}` : 'No disponible'}</Row>
                {rejected && <Row label="Motivo del rechazo">{reasonText(payment.reason_code)}</Row>}
            </dl>
            <h3>Conceptos</h3>
            <ul className={styles.lines}>
                {payment.lines.map((line, index) => <li key={`${line.code}-${index}`}>
                    <span>{line.description}</span><strong>{paymentAmount(line.amount, payment.currency)}</strong>
                </li>)}
            </ul>
            {rejected && <p className={styles.note}>No se realizó ningún cargo ni se modificó tu plan.</p>}
        </article>}
        <Link to="/payments/history">Volver al historial</Link>
    </section>;
}

export function PaymentDetailPage() {
    const { paymentId } = useParams();
    const { user } = useAuth();
    return <Detail key={`${user.id}:${paymentId}`} paymentId={paymentId} />;
}
