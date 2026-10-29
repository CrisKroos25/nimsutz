import { useEffect, useState } from 'react';
import { Check, CreditCard, Info, X } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../shared/auth/AuthContext';
import Button from '../../shared/components/Button/Button';
import Input from '../../shared/components/Input/Input';
import Modal from '../../shared/components/Modal/Modal';
import { formatStorage } from '../../shared/utils/planFormat';
import { getPaymentResult, getQuote } from './api/paymentsApi';
import usePaymentAttempt from './hooks/usePaymentAttempt';
import { checkoutCard, formatCardNumber, formatExpiry, paymentAmount, paymentPeriod } from './paymentPresentation';
import styles from './PaymentPages.module.css';

const reasons = {
    card_not_found: 'No pudimos encontrar la tarjeta. Revisa el número e inténtalo de nuevo.',
    card_details_invalid: 'Los datos de la tarjeta no coinciden. Revísalos antes de volver a intentar.',
    card_disabled: 'La tarjeta está deshabilitada. Intenta con otra tarjeta.',
    card_expired: 'La tarjeta está vencida. Intenta con otra tarjeta.',
    currency_mismatch: 'La moneda de la tarjeta no es compatible con este pago.',
    insufficient_funds: 'La tarjeta no tiene saldo suficiente para completar el pago.',
};
const operationLabels = { contract: 'Contratación', renew: 'Renovación', change: 'Cambio de plan' };
const dateTime = (value) => new Date(value).toLocaleString('es-GT', {
    timeZone: 'America/Guatemala', dateStyle: 'medium', timeStyle: 'short',
});

function DetailRow({ label, children, className = '' }) {
    return <div className={`${styles.detailRow} ${className}`}><dt>{label}</dt><dd>{children}</dd></div>;
}

function QuoteSummary({ quote }) {
    return <aside className={`${styles.card} ${styles.summary}`} aria-labelledby="summary-title">
        <span className={styles.badge}>{operationLabels[quote.operation] || 'Resumen del pago'}</span>
        <h2 id="summary-title">Plan {quote.plan.name}</h2>
        <dl className={styles.details}>
            <DetailRow label="Capacidad">{formatStorage(quote.plan.capacity_bytes)}</DetailRow>
            <DetailRow label="Periodo">{paymentPeriod(quote.effect.starts_at, quote.effect.ends_at)}</DetailRow>
            {quote.lines.map((line, index) => <DetailRow key={`${line.code}-${index}`} label={line.description}>
                {paymentAmount(line.amount, quote.currency)}
            </DetailRow>)}
            <DetailRow label="Total de hoy" className={styles.total}>{paymentAmount(quote.total, quote.currency)}</DetailRow>
        </dl>
        <p className={styles.note}>Importes en {quote.currency}. El total es calculado por Nim sutz’ y no se puede editar.</p>
        {quote.effect.scheduled_change_at && <p className={styles.notice}>
            <Info size={16} aria-hidden="true" />
            El cambio programado se aplicará el {dateTime(quote.effect.scheduled_change_at)}.
        </p>}
        <p className={styles.validUntil}>Condiciones vigentes hasta el {dateTime(quote.expires_at)}.</p>
    </aside>;
}

function CardFields({ disabled, fields }) {
    const [number, setNumber] = useState('');
    const [expiry, setExpiry] = useState('');
    return <fieldset disabled={disabled} className={styles.fields}>
        <legend className={styles.srOnly}>Datos de la tarjeta</legend>
        <Input label="Número de tarjeta" name="number" inputMode="numeric" placeholder="0000 0000 0000 0000"
            pattern="[0-9]{4} [0-9]{4} [0-9]{4} [0-9]{4}" maxLength={19} required
            value={number} onChange={event => setNumber(formatCardNumber(event.target.value))}
            leadingIcon={<CreditCard size={18} />} className={styles.cardInput} error={fields.number?.[0]} />
        <Input label="Nombre en la tarjeta" name="holder" placeholder="Como aparece en tu tarjeta"
            maxLength={120} required className={styles.cardInput} error={fields.holder?.[0]} />
        <div className={styles.fieldPair}>
            <Input label="Fecha de vencimiento" name="expiry" inputMode="numeric" placeholder="MM/AA"
                pattern="(0[1-9]|1[0-2])/[0-9]{2}" maxLength={5} required value={expiry}
                onChange={event => setExpiry(formatExpiry(event.target.value))} className={styles.cardInput}
                error={fields.expiry_month?.[0] || fields.expiry_year?.[0]} />
            <Input label="Código de seguridad" name="security_code" type="password" inputMode="numeric"
                placeholder="CVV" pattern="[0-9]{3}" maxLength={3} required className={styles.cardInput}
                hint="3 dígitos al reverso de tu tarjeta" error={fields.security_code?.[0]} />
        </div>
    </fieldset>;
}

function Checkout({ quoteId, userId, initialQuote }) {
    const navigate = useNavigate();
    const [quote, setQuote] = useState(initialQuote || null);
    const [loadError, setLoadError] = useState('');
    const [reload, setReload] = useState(0);
    const { pending, hasRequest, busy, error, fields, run } = usePaymentAttempt(`${userId}:${quoteId}`);
    useEffect(() => {
        if (initialQuote) return;
        let active = true;
        getQuote(quoteId).then(data => {
            if (!data?.quote?.plan || !Array.isArray(data.quote.lines) || !data.quote.effect) {
                throw new Error('No se recibió un resumen comercial válido.');
            }
            if (active) { setQuote(data.quote); setLoadError(''); }
        }).catch(error => { if (active) setLoadError(error.message); });
        return () => { active = false; };
    }, [quoteId, reload, initialQuote]);

    async function process(body) {
        const result = await run(body);
        if (!result) return;
        try {
            sessionStorage.setItem(`payment-result:${userId}:${result.payment.id}`, quoteId);
        } catch { /* El resultado sigue disponible en el servidor aunque no se conserve el enlace de reintento. */ }
        navigate(`/payments/result/${result.payment.id}`, { replace: true, state: { checkoutQuote: quote } });
    }
    function submit(event) {
        event.preventDefault();
        process({ quote_id: quoteId, card: checkoutCard(new FormData(event.currentTarget)) });
    }
    const paymentLabel = quote ? `Pagar ${paymentAmount(quote.total, quote.currency)}${
        quote.operation === 'contract' ? ' y activar plan' : quote.operation === 'renew' ? ' y renovar' : ' y confirmar cambio'
    }` : 'Confirmar pago';

    return <section className={styles.page} aria-busy={busy}>
        <header className={styles.pageHeading}>
            <p className={styles.eyebrow}>{operationLabels[quote?.operation] || 'Contratación'} y pago</p>
            <h1>{quote?.operation === 'renew' ? 'Confirma tu renovación' : quote?.operation === 'change' ? 'Confirma tu cambio de plan' : 'Confirma tu plan'}</h1>
        </header>
        {(error || loadError) && <p className={styles.alert} role="alert">{error || loadError}</p>}
        {loadError && <Button variant="secondary" onClick={() => setReload(reload + 1)}>Volver a consultar el resumen</Button>}
        {!quote && !loadError && <p className={styles.notice} role="status">Cargando resumen del pago…</p>}
        {pending && <div className={styles.notice} role="status">
            <div>
                <p>Estamos verificando el resultado de tu pago.</p>
                {!hasRequest && <p>Si vuelves a enviarlo, utiliza los mismos datos de la tarjeta.</p>}
                <Button variant="secondary" onClick={() => process()} loading={busy}>Consultar resultado</Button>
            </div>
        </div>}
        <div className={styles.checkoutGrid}>
            {(quote?.requires_payment || pending) && <form className={`${styles.card} ${styles.paymentForm}`} onSubmit={submit} autoComplete="off">
                <div className={styles.formHeading}>
                    <h2>Datos de la tarjeta</h2>
                    <p>Completa tus datos para confirmar el pago.</p>
                </div>
                <CardFields disabled={busy || Boolean(pending && hasRequest)} fields={fields} />
                <div className={styles.formActions}>
                    <Button className={styles.pillButton} type="submit" loading={busy} loadingLabel="Procesando…">
                        {pending ? 'Reintentar pago' : paymentLabel}
                    </Button>
                    {!busy && <Link className={styles.secondaryAction} to="/plans/summary">{pending ? 'Volver a planes' : 'Cancelar'}</Link>}
                </div>
                <p className={styles.note}>Un solo pago. Sin cargos automáticos.</p>
            </form>}
            {quote && <QuoteSummary quote={quote} />}
        </div>
        {quote && !quote.requires_payment && <div className={styles.notice}>
            <p>Este cambio no requiere pago. Confírmalo desde la selección de suscripción.</p>
            <Link to="/plans/summary">Volver a mi selección</Link>
        </div>}
        {!quote && !pending && !busy && <Link to="/plans/summary">Volver a planes</Link>}
    </section>;
}

export function CheckoutPage() {
    const { quoteId } = useParams();
    const { user } = useAuth();
    return <Checkout key={`${user.id}:${quoteId}`} quoteId={quoteId} userId={user.id} />;
}

function PaymentResult({ paymentId }) {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, refresh } = useAuth();
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    const [continuing, setContinuing] = useState(false);
    useEffect(() => {
        let active = true;
        getPaymentResult(paymentId).then(data => {
            if (active) { setResult(data); setError(''); }
        }).catch(error => { if (active) setError(error.message); });
        return () => { active = false; };
    }, [paymentId, attempt]);
    const approved = result?.payment.status === 'approved';
    const quoteId = sessionStorage.getItem(`payment-result:${user.id}:${paymentId}`);
    async function continueToAccount() {
        setContinuing(true);
        await refresh();
        navigate(result.destination === 'files' ? '/files' : '/plans');
    }
    const subscription = result?.subscription;
    const message = approved
        ? result.payment.operation === 'renew' ? 'La renovación de tu plan se completó.'
            : result.payment.operation === 'change' ? 'El cambio de plan se completó.'
                : subscription ? `Tu plan ${subscription.plan.name} está activo.` : 'Tu pago se completó correctamente.'
        : reasons[result?.payment.reason_code] || 'No pudimos completar el pago. Revisa los datos e inténtalo de nuevo.';

    const paymentDetails = result && <>
        <dl className={styles.details}>
            <DetailRow label="Referencia"><span className={styles.reference}>{result.payment.reference}</span></DetailRow>
            <DetailRow label={approved ? 'Monto cobrado' : 'Importe solicitado'}>
                {paymentAmount(result.payment.amount, result.payment.currency)} <span className={styles.currency}>{result.payment.currency}</span>
            </DetailRow>
            <DetailRow label="Tarjeta">{result.payment.card_last4 ? `•••• ${result.payment.card_last4}` : 'No disponible'}</DetailRow>
            {subscription && <>
                <DetailRow label={approved ? 'Plan' : 'Plan actual'}>{subscription.plan.name} · {formatStorage(subscription.plan.capacity_bytes)}</DetailRow>
                <DetailRow label="Vigencia">{paymentPeriod(subscription.started_at, subscription.expires_at)}</DetailRow>
            </>}
        </dl>
        <p className={styles.note}>{dateTime(result.payment.created_at)}</p>
    </>;

    if (approved) {
        const backgroundQuote = location.state?.checkoutQuote;
        return <>
            <div inert aria-hidden="true">
                {backgroundQuote ? <Checkout quoteId={backgroundQuote.id} userId={user.id} initialQuote={backgroundQuote} />
                    : <section className={styles.page}>
                        <p className={styles.eyebrow}>Planes y suscripciones</p>
                        <h1>Tu suscripción</h1>
                        {subscription && <div className={styles.card}>
                            <h2>Plan {subscription.plan.name}</h2>
                            <p>{formatStorage(subscription.plan.capacity_bytes)}</p>
                        </div>}
                    </section>}
            </div>
            <Modal open onClose={() => navigate('/')} className={styles.approvedDialog}
                title={<>
                    <span className={`${styles.statusIcon} ${styles.approved}`} aria-hidden="true"><Check size={30} strokeWidth={2} /></span>
                    <span>Pago aprobado</span>
                </>}
                description={message}>
                {paymentDetails}
                <Button className={styles.pillButton} onClick={continueToAccount} loading={continuing}>
                    {result.destination === 'files' ? 'Ir a mis archivos' : 'Continuar'}
                </Button>
                <Link className={styles.secondaryAction} to="/">Volver al inicio</Link>
                <button type="button" className={styles.closeDialog} onClick={() => navigate('/')} aria-label="Cerrar y volver al inicio">
                    <X size={20} aria-hidden="true" />
                </button>
            </Modal>
        </>;
    }

    return <section className={styles.page}>
        <p className={styles.eyebrow}>Resultado del pago</p>
        <div className={`${styles.card} ${styles.resultCard}`}>
            {result && <div className={`${styles.statusIcon} ${styles.rejected}`} aria-hidden="true">
                <X size={28} strokeWidth={2} />
            </div>}
            <h1>{result ? 'Pago rechazado' : 'Resultado del pago'}</h1>
            {error && <><p className={styles.alert} role="alert">{error}</p><Button variant="secondary" onClick={() => setAttempt(attempt + 1)}>Consultar nuevamente</Button></>}
            {!result && !error && <p className={styles.resultDescription} role="status">Consultando resultado…</p>}
            {result && <>
                <p className={styles.resultDescription}>{message}</p>
                {paymentDetails}
                <p className={styles.note}>No se realizó ningún cargo ni se modificó tu plan.</p>
                <Link className={styles.primaryAction} to={quoteId ? `/payments/checkout/${quoteId}` : '/plans/summary'}>
                    {quoteId ? 'Corregir datos e intentar de nuevo' : 'Volver a elegir mi plan'}
                </Link>
            </>}
            <Link className={styles.secondaryAction} to="/">Volver al inicio</Link>
        </div>
    </section>;
}

export function PaymentResultPage() {
    const { paymentId } = useParams();
    const { user } = useAuth();
    return <PaymentResult key={`${user.id}:${paymentId}`} paymentId={paymentId} />;
}
