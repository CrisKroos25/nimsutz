import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../shared/auth/AuthContext';
import Button from '../../shared/components/Button/Button';
import Input from '../../shared/components/Input/Input';
import { formatStorage } from '../../shared/utils/planFormat';
import { getPaymentResult, getQuote } from './api/paymentsApi';
import usePaymentAttempt from './hooks/usePaymentAttempt';
import styles from './PaymentPages.module.css';

const reasons = {
    card_not_found: 'La tarjeta ficticia no existe.',
    card_details_invalid: 'Los datos de la tarjeta no coinciden.',
    card_disabled: 'La tarjeta está deshabilitada.',
    card_expired: 'La tarjeta está vencida.',
    currency_mismatch: 'La moneda de la tarjeta no coincide.',
    insufficient_funds: 'La tarjeta no tiene saldo suficiente.',
};
const date = (value) => new Date(value).toLocaleString('es-GT', { timeZone: 'America/Guatemala' });

function QuoteSummary({ quote }) {
    return <>
        <h2>{quote.plan.name}</h2>
        <p>Capacidad: {formatStorage(quote.plan.capacity_bytes)}</p>
        <ul>{quote.lines.map((line, index) => <li key={`${line.code}-${index}`}>{line.description}: {line.amount} {quote.currency}</li>)}</ul>
        <p><strong>Total: {quote.total} {quote.currency}</strong></p>
        <p>Resumen vigente hasta: {date(quote.expires_at)}</p>
        {quote.effect.starts_at && <p>Inicio previsto: {date(quote.effect.starts_at)}</p>}
        {quote.effect.ends_at && <p>Fin previsto: {date(quote.effect.ends_at)}</p>}
        {quote.effect.scheduled_change_at && <p>El cambio programado se aplicará el {date(quote.effect.scheduled_change_at)}.</p>}
    </>;
}

function Checkout({ quoteId, userId }) {
    const navigate = useNavigate();
    const [quote, setQuote] = useState(null);
    const [loadError, setLoadError] = useState('');
    const [reload, setReload] = useState(0);
    const { pending, hasRequest, busy, error, fields, run } = usePaymentAttempt(`${userId}:${quoteId}`);
    useEffect(() => {
        let active = true;
        getQuote(quoteId).then(data => {
            if (!data?.quote?.plan || !Array.isArray(data.quote.lines) || !data.quote.effect) {
                throw new Error('No se recibió un resumen comercial válido.');
            }
            if (active) { setQuote(data.quote); setLoadError(''); }
        }).catch(error => { if (active) setLoadError(error.message); });
        return () => { active = false; };
    }, [quoteId, reload]);

    async function process(body) {
        const result = await run(body);
        if (!result) return;
        try {
            sessionStorage.setItem(`payment-result:${userId}:${result.payment.id}`, quoteId);
        } catch { /* El resultado sigue disponible en el servidor aunque no se conserve el enlace de reintento. */ }
        navigate(`/payments/result/${result.payment.id}`, { replace: true });
    }
    function submit(event) {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        process({
            quote_id: quoteId,
            card: {
                number: form.get('number'), holder: form.get('holder'),
                expiry_month: Number(form.get('expiry_month')), expiry_year: Number(form.get('expiry_year')),
                security_code: form.get('security_code'),
            },
        });
    }
    return <section className={styles.panel} aria-busy={busy}>
        <h1>Pago de prueba</h1>
        <p>Utiliza únicamente las tarjetas ficticias del proyecto.</p>
        {(error || loadError) && <p role="alert">{error || loadError}</p>}
        {loadError && <Button onClick={() => setReload(reload + 1)}>Volver a consultar el resumen</Button>}
        {!quote && !loadError && <p role="status">Cargando resumen…</p>}
        {quote && <QuoteSummary quote={quote} />}
        {pending && <div role="status">
            <p>Hay un intento pendiente. Consulta su resultado antes de continuar.</p>
            {!hasRequest && <p>Para reenviarlo tras recargar, ingresa exactamente los datos originales. Se conservará la misma clave.</p>}
            <Button onClick={() => process()} loading={busy}>Consultar resultado</Button>
        </div>}
        {quote && !quote.requires_payment && <p>Esta operación no requiere checkout. Confírmala desde la selección de suscripción.</p>}
        {(quote?.requires_payment || pending) && <form onSubmit={submit} autoComplete="off">
            <fieldset disabled={busy || Boolean(pending && hasRequest)} className={styles.fields}>
                <legend>Datos de tarjeta ficticia</legend>
                <Input label="Número ficticio" name="number" inputMode="numeric" pattern="[0-9]{16}" maxLength={16} required error={fields.number?.[0]} />
                <Input label="Titular de prueba" name="holder" maxLength={120} required error={fields.holder?.[0]} />
                <Input label="Mes de vencimiento" name="expiry_month" type="number" min="1" max="12" required error={fields.expiry_month?.[0]} />
                <Input label="Año de vencimiento" name="expiry_year" type="number" min="2000" max="9999" required error={fields.expiry_year?.[0]} />
                <Input label="Código ficticio" name="security_code" type="password" inputMode="numeric" pattern="[0-9]{3}" maxLength={3} required error={fields.security_code?.[0]} />
            </fieldset>
            <Button type="submit" loading={busy} loadingLabel="Procesando pago…">
                {pending ? 'Reintentar la misma operación' : 'Confirmar pago de prueba'}
            </Button>
        </form>}
        {!busy && <Link to="/plans/summary">{pending ? 'Volver a planes (el intento se conserva)' : 'Cancelar y volver a planes'}</Link>}
    </section>;
}

export function CheckoutPage() {
    const { quoteId } = useParams();
    const { user } = useAuth();
    return <Checkout key={`${user.id}:${quoteId}`} quoteId={quoteId} userId={user.id} />;
}

function PaymentResult({ paymentId }) {
    const navigate = useNavigate();
    const { user, refresh } = useAuth();
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
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
        await refresh();
        navigate(result.destination === 'files' ? '/files' : '/plans');
    }
    return <section className={styles.panel}>
        <h1>{result ? approved ? 'Pago aprobado' : 'Pago rechazado' : 'Resultado del pago'}</h1>
        {error && <><p role="alert">{error}</p><Button onClick={() => setAttempt(attempt + 1)}>Consultar nuevamente</Button></>}
        {!result && !error && <p role="status">Consultando resultado…</p>}
        {result && <>
            <p>{approved ? 'La operación se completó.' : reasons[result.payment.reason_code] || 'El pago fue rechazado.'}</p>
            <p>Referencia: {result.payment.reference}</p>
            <p>{result.payment.amount} {result.payment.currency} · Tarjeta terminada en {result.payment.card_last4 || '—'}</p>
            <p>Fecha: {date(result.payment.created_at)}</p>
            {result.subscription && <>
                <p>Plan: {result.subscription.plan.name} · {formatStorage(result.subscription.plan.capacity_bytes)}</p>
                {result.subscription.started_at && <p>Inicio: {date(result.subscription.started_at)}</p>}
                {result.subscription.expires_at && <p>Vencimiento: {date(result.subscription.expires_at)}</p>}
            </>}
            {!approved && quoteId && <Link to={`/payments/checkout/${quoteId}`}>Corregir datos e iniciar otro intento</Link>}
            {approved && <Button onClick={continueToAccount}>Continuar</Button>}
        </>}
        <Link to="/">Volver al inicio</Link>
    </section>;
}

export function PaymentResultPage() {
    const { paymentId } = useParams();
    const { user } = useAuth();
    return <PaymentResult key={`${user.id}:${paymentId}`} paymentId={paymentId} />;
}
