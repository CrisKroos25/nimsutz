import { useCallback, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getAccountOverview } from '../../shared/api/accountApi';
import { useAuth } from '../../shared/auth/AuthContext';
import Badge from '../../shared/components/Badge/Badge';
import Button from '../../shared/components/Button/Button';
import { useRemoteData } from '../../shared/hooks/useRemoteData';
import { usePlans } from '../../shared/hooks/usePlans';
import { formatStorage } from '../../shared/utils/planFormat';
import { paymentAmount, paymentPeriod } from '../payments/paymentPresentation';
import {
    cancelScheduledChange, confirmScheduledQuote, createQuote, getCurrentSubscription,
} from './subscriptionApi';
import {
    EFFECT_LABELS, changeTargets, coverageEnd, formatDay, isExpired, isFree, newOperationKey, nextStep,
    quoteErrorMessage, quotaState,
} from './subscriptionModel';
import styles from './SubscriptionPages.module.css';

const PLAN_NAMES = { free: 'Gratis', basic: 'Básico', premium: 'Premium' };
const targetName = (code) => PLAN_NAMES[code] || code;

function Row({ label, children }) {
    return <div className={styles.row}><dt>{label}</dt><dd>{children}</dd></div>;
}

function Failure({ message, onRetry }) {
    return <div className={styles.alert} role="alert">
        <p>{message}</p>
        {onRetry && <Button variant="secondary" onClick={onRetry}>Reintentar</Button>}
    </div>;
}

// ---------- Mi suscripción (R10) ----------

function MySubscription() {
    const load = useCallback(async () => {
        const [current, overview] = await Promise.all([getCurrentSubscription(), getAccountOverview()]);
        return { ...current, usage: quotaState(overview.storage), storage: overview.storage };
    }, []);
    const { loading, data, error, reload } = useRemoteData(load);
    const [confirmingCancel, setConfirmingCancel] = useState(false);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState('');
    const working = useRef(false);

    async function cancelChange() {
        if (working.current) return;
        working.current = true;
        setBusy(true);
        try {
            await cancelScheduledChange();
            setConfirmingCancel(false);
            setNotice('El cambio programado se canceló. Tu plan y tus pagos siguen igual.');
            reload();
        } catch (failure) {
            setNotice(quoteErrorMessage(failure));
        } finally { working.current = false; setBusy(false); }
    }

    const subscription = data?.subscription;
    const end = coverageEnd(subscription);
    return <section className={styles.page} aria-labelledby="subscription-title">
        <header className={styles.heading}>
            <h1 id="subscription-title">Mi suscripción</h1>
            <p>Consulta tu plan, tu consumo y las operaciones disponibles.</p>
        </header>
        {notice && <p className={styles.notice} role="status">{notice}</p>}
        {loading ? <p role="status">Consultando tu suscripción…</p> : error ?
            <Failure message={quoteErrorMessage(error)} onRetry={reload} /> : !subscription ?
                <article className={styles.card}>
                    <h2>Sin plan activo</h2>
                    <p>Elige y confirma un plan para habilitar tu almacenamiento.</p>
                    <Link className={styles.primaryLink} to="/plans">Elegir plan</Link>
                </article> : <>
                    <div className={styles.grid}>
                        <article className={styles.card} aria-labelledby="plan-title">
                            <div className={styles.cardHead}>
                                <h2 id="plan-title">Plan {subscription.plan.name}</h2>
                                <Badge tone="success">Activo</Badge>
                            </div>
                            <dl className={styles.details}>
                                <Row label="Capacidad">{formatStorage(subscription.plan.capacity_bytes)}</Row>
                                <Row label="Inicio">{formatDay(subscription.started_at)}</Row>
                                <Row label="Vigencia">{isFree(subscription) ? 'No vence' : end ? `Hasta el ${formatDay(end)}` : 'No disponible'}</Row>
                                {data.nextCycle && <Row label="Siguiente ciclo pagado">{paymentPeriod(data.nextCycle.starts_at, data.nextCycle.ends_at)}</Row>}
                            </dl>
                        </article>
                        <article className={styles.card} aria-labelledby="usage-title">
                            <h2 id="usage-title">Consumo</h2>
                            {data.usage ? <>
                                <p className={styles.usage}>{formatStorage(data.storage.used_bytes)} usados de {formatStorage(data.storage.capacity_bytes)}</p>
                                <progress max={data.storage.capacity_bytes} value={Math.min(data.storage.used_bytes, data.storage.capacity_bytes)}
                                    aria-label="Almacenamiento usado" className={styles.meter} />
                                <p className={styles.muted}>{data.usage.percent} % · {formatStorage(data.usage.available)} disponibles. La papelera también ocupa espacio.</p>
                                {data.usage.exceeded && <p className={styles.warning} role="status">
                                    Superas la capacidad de tu plan. Puedes consultar, descargar y eliminar archivos, pero no subir ni restaurar hasta liberar espacio.
                                </p>}
                            </> : <p className={styles.muted}>No se pudo confirmar tu consumo.</p>}
                        </article>
                    </div>

                    {data.scheduledChange && <article className={styles.card} aria-labelledby="scheduled-title">
                        <h2 id="scheduled-title">Cambio programado</h2>
                        <p>Pasarás a <strong>{targetName(data.scheduledChange.target_plan_code)}</strong> el {formatDay(data.scheduledChange.effective_at)}. Hasta entonces conservas tu plan actual.</p>
                        {confirmingCancel ? <div className={styles.actions}>
                            <p>¿Cancelar este cambio? No se elimina tu cobertura ni tus pagos.</p>
                            <Button variant="danger" loading={busy} onClick={cancelChange}>Sí, cancelar cambio</Button>
                            <Button variant="secondary" disabled={busy} onClick={() => setConfirmingCancel(false)}>Volver</Button>
                        </div> : <Button variant="secondary" onClick={() => setConfirmingCancel(true)}>Cancelar cambio programado</Button>}
                    </article>}

                    <article className={styles.card} aria-labelledby="actions-title">
                        <h2 id="actions-title">Operaciones disponibles</h2>
                        <div className={styles.actions}>
                            {data.allowed.includes('renew') && <Link className={styles.primaryLink} to="/subscription/renew">Renovar mi plan</Link>}
                            {data.allowed.includes('change') && <Link className={styles.secondaryLink} to="/subscription/change">Cambiar de plan</Link>}
                            {data.allowed.includes('contract') && <Link className={styles.primaryLink} to="/plans">Elegir plan</Link>}
                        </div>
                        {isFree(subscription) && <p className={styles.muted}>El plan Gratis no vence ni se renueva. Puedes mejorarlo cuando quieras.</p>}
                        {!isFree(subscription) && !data.allowed.includes('renew') && <p className={styles.muted}>Ya tienes un ciclo siguiente pagado, así que no hay renovación disponible por ahora.</p>}
                    </article>
                </>}
        <nav className={styles.links} aria-label="Accesos relacionados">
            <Link to="/payments/history">Ver historial de pagos</Link>
            <Link to="/profile">Volver a mi perfil</Link>
        </nav>
    </section>;
}

export function SubscriptionPage() {
    const { user } = useAuth();
    return <MySubscription key={user.id} />;
}

// ---------- Resumen de una cotización (compartido por renovar y cambiar) ----------

function QuoteSummary({ quote }) {
    return <article className={styles.card} aria-labelledby="quote-title">
        <h2 id="quote-title">Resumen: plan {quote.plan.name}</h2>
        <dl className={styles.details}>
            <Row label="Capacidad">{formatStorage(quote.plan.capacity_bytes)}</Row>
            {quote.effect.starts_at && <Row label="Periodo">{paymentPeriod(quote.effect.starts_at, quote.effect.ends_at)}</Row>}
            {quote.lines.map((line, index) => <Row key={`${line.code}-${index}`} label={line.description}>{paymentAmount(line.amount, quote.currency)}</Row>)}
            <Row label="Total"><strong>{paymentAmount(quote.total, quote.currency)}</strong></Row>
        </dl>
        <p className={styles.muted}>{EFFECT_LABELS[quote.effect.kind]}</p>
        {quote.effect.scheduled_change_at && <p className={styles.muted}>Fecha del cambio: {formatDay(quote.effect.scheduled_change_at)}.</p>}
        <p className={styles.muted}>Importes en {quote.currency}, calculados por Nim sutz’. Condiciones vigentes hasta las {new Date(quote.expires_at).toLocaleTimeString('es-GT', { timeZone: 'America/Guatemala', hour: '2-digit', minute: '2-digit' })}.</p>
    </article>;
}

// Un solo envío a la vez, y la clave de idempotencia se conserva por cotización para reintentar sin duplicar.
function useQuoteFlow() {
    const [quote, setQuote] = useState(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [done, setDone] = useState(null);
    const working = useRef(false);
    const keys = useRef(new Map());

    async function request(operation, planVersionId, onConflict) {
        if (working.current) return;
        working.current = true;
        setBusy(true); setError(''); setQuote(null); setDone(null);
        try { setQuote(await createQuote(operation, planVersionId)); }
        catch (failure) {
            setError(quoteErrorMessage(failure));
            if (failure.status === 409) onConflict?.();
        } finally { working.current = false; setBusy(false); }
    }

    async function confirm() {
        if (working.current || !quote) return;
        working.current = true;
        setBusy(true); setError('');
        if (!keys.current.has(quote.id)) keys.current.set(quote.id, newOperationKey());
        try {
            const result = await confirmScheduledQuote(quote.id, keys.current.get(quote.id));
            setDone(result?.scheduled_change || {});
        } catch (failure) { setError(quoteErrorMessage(failure)); }
        finally { working.current = false; setBusy(false); }
    }

    return { quote, busy, error, done, request, confirm, reset: () => { setQuote(null); setError(''); setDone(null); } };
}

function PayOrConfirm({ flow, onNewQuote }) {
    const navigate = useNavigate();
    const { quote } = flow;
    const step = nextStep(quote);
    if (isExpired(quote)) {
        return <div className={styles.actions}>
            <p className={styles.notice} role="status">El resumen venció. Genera uno nuevo para continuar.</p>
            <Button loading={flow.busy} onClick={onNewQuote}>Generar resumen nuevo</Button>
        </div>;
    }
    return <div className={styles.actions}>
        {step === 'checkout' && <Button onClick={() => navigate(`/payments/checkout/${quote.id}`)}>Continuar al pago</Button>}
        {step === 'confirm' && <Button loading={flow.busy} loadingLabel="Confirmando…" onClick={flow.confirm}>Confirmar cambio programado</Button>}
        {step === 'none' && <p className={styles.muted}>Esta operación no se puede completar desde aquí.</p>}
        <Button variant="secondary" disabled={flow.busy} onClick={flow.reset}>Cancelar</Button>
    </div>;
}

// ---------- Renovación (R11) ----------

function Renew() {
    const load = useCallback(() => getCurrentSubscription(), []);
    const { loading, data, error, reload } = useRemoteData(load);
    const flow = useQuoteFlow();
    const allowed = data?.allowed.includes('renew');
    return <section className={styles.page} aria-labelledby="renew-title">
        <header className={styles.heading}>
            <h1 id="renew-title">Renovar mi plan</h1>
            <p>Revisa el resumen que calcula el servidor antes de pasar al pago.</p>
        </header>
        {loading ? <p role="status">Consultando tu suscripción…</p> : error ? <Failure message={quoteErrorMessage(error)} onRetry={reload} /> :
            !allowed ? <article className={styles.card}>
                <h2>Renovación no disponible</h2>
                <p>{!data.subscription ? 'Aún no tienes un plan que renovar.'
                    : isFree(data.subscription) ? 'El plan Gratis no vence ni se renueva.'
                        : 'Ya tienes un ciclo siguiente pagado. No se puede renovar más por ahora.'}</p>
                <Link className={styles.secondaryLink} to="/subscription">Volver a mi suscripción</Link>
            </article> : <>
                <article className={styles.card}>
                    <h2>Plan actual: {data.subscription.plan.name}</h2>
                    <p className={styles.muted}>Tu cobertura termina el {formatDay(coverageEnd(data.subscription))}. La renovación conserva las condiciones que contrataste.</p>
                    {!flow.quote && <Button loading={flow.busy} loadingLabel="Calculando…" onClick={() => flow.request('renew')}>Ver resumen de renovación</Button>}
                </article>
                {flow.error && <Failure message={flow.error} />}
                {flow.quote && <><QuoteSummary quote={flow.quote} /><PayOrConfirm flow={flow} onNewQuote={() => flow.request('renew')} /></>}
            </>}
        <Link to="/subscription">Volver a mi suscripción</Link>
    </section>;
}

export function RenewPage() {
    const { user } = useAuth();
    return <Renew key={user.id} />;
}

// ---------- Cambio de plan (R11) ----------

function ChangePlan() {
    const loadCurrent = useCallback(() => getCurrentSubscription(), []);
    const current = useRemoteData(loadCurrent);
    const catalog = usePlans();
    const flow = useQuoteFlow();
    const [target, setTarget] = useState(null);
    const choose = (plan) => { setTarget(plan); flow.request('change', plan.version_id, catalog.reload); };
    const loading = current.loading || catalog.loading;
    const failure = current.error ? quoteErrorMessage(current.error) : catalog.error;
    const allowed = current.data?.allowed.includes('change');
    const subscription = current.data?.subscription;
    return <section className={styles.page} aria-labelledby="change-title">
        <header className={styles.heading}>
            <h1 id="change-title">Cambiar de plan</h1>
            <p>Elige el plan al que quieres pasar y revisa el resumen antes de continuar.</p>
        </header>
        {loading ? <p role="status">Consultando planes y suscripción…</p> : failure ?
            <Failure message={failure} onRetry={() => { current.reload(); catalog.reload(); }} /> :
            !subscription ? <article className={styles.card}>
                <h2>Aún no tienes un plan</h2>
                <p>Primero elige y confirma uno.</p>
                <Link className={styles.primaryLink} to="/plans">Elegir plan</Link>
            </article> : !allowed ? <article className={styles.card}>
                <h2>Cambio no disponible</h2>
                <p>No puedes cambiar de plan en este momento.</p>
            </article> : flow.done ? <article className={styles.card} role="status">
                <h2>Cambio programado</h2>
                <p>Pasarás a <strong>{flow.quote.plan.name}</strong>{flow.done.effective_at ? ` el ${formatDay(flow.done.effective_at)}` : ' al terminar tu cobertura'}. Hasta entonces conservas tu plan actual y no se cobró nada.</p>
                <Link className={styles.primaryLink} to="/subscription">Ir a mi suscripción</Link>
            </article> : <>
                <p className={styles.muted}>Plan actual: <strong>{subscription.plan.name}</strong></p>
                <div className={styles.grid}>
                    {changeTargets(catalog.plans, subscription).map(({ plan, selectable }) => <article className={styles.card} key={plan.version_id}>
                        <h2>{plan.name}</h2>
                        <p>{paymentAmount(plan.price, plan.currency)}{plan.period ? ` / ${plan.period}` : ''}</p>
                        <p className={styles.muted}>{formatStorage(plan.capacity_bytes)} de almacenamiento</p>
                        {selectable ? <Button variant="secondary" disabled={flow.busy && target?.version_id !== plan.version_id}
                            loading={flow.busy && target?.version_id === plan.version_id && !flow.quote} loadingLabel="Calculando…"
                            onClick={() => choose(plan)}>Ver resumen de {plan.name}</Button>
                            : <p className={styles.muted}>No disponible por el momento.</p>}
                    </article>)}
                </div>
                {flow.error && <Failure message={flow.error} />}
                {flow.quote && <><QuoteSummary quote={flow.quote} /><PayOrConfirm flow={flow} onNewQuote={() => target && choose(target)} /></>}
            </>}
        <Link to="/subscription">Volver a mi suscripción</Link>
    </section>;
}

export function ChangePlanPage() {
    const { user } = useAuth();
    return <ChangePlan key={user.id} />;
}
