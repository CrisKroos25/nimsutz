import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import { readPlanPreference, readPlanIntent, savePlanIntent, clearPlanPreference, resolvePlanSelection } from '@shared/auth/accessFlow';
import { getPlans, getPreference, setPreference, selectPlan, getSubscription, validateSubscription, activateFree, serviceMessage } from '@shared/api/accountApi';
import { usePlans } from '@shared/hooks/usePlans';
import { createQuote } from '@features/subscription/subscriptionApi';
import { quoteErrorMessage } from '@features/subscription/subscriptionModel';
import { formatStorage } from '@shared/utils/planFormat';
import { FALLBACK_PLANS } from '@shared/planInformation';
import Button from '@shared/components/Button/Button';
import styles from './PlansPage.module.css';

export default function PlansPage() {
    const { user, refresh } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const summary = location.pathname.endsWith('/summary');

    // Planes: única fuente compartida con el resto de la app.
    const { plans, loading: plansLoading, error: plansError, reload: reloadPlans, replace: replacePlans } = usePlans();

    // Datos de la cuenta: solo le importan a esta página.
    const [account, setAccount] = useState({ loading: true, subscription: null, preference: null, error: '' });
    const [accountAttempt, setAccountAttempt] = useState(0);

    const [selected, setSelected] = useState(null);
    const [notice, setNotice] = useState('');
    const [intentError, setIntentError] = useState('');
    const [busy, setBusy] = useState(false);
    const [intent, setIntent] = useState(readPlanIntent);
    const submitting = useRef(false);

    const loading = plansLoading || account.loading;
    const error = plansError || account.error;
    const loaded = !loading && !error;

    useEffect(() => {
        let active = true;
        setAccount((previous) => ({ ...previous, loading: true, error: '' }));
        Promise.all([getSubscription(), getPreference()])
            .then(([current, preference]) => active && setAccount({
                loading: false, subscription: validateSubscription(current), preference, error: '',
            }))
            .catch((failure) => active && setAccount({
                loading: false, subscription: null, preference: null,
                error: serviceMessage(failure, 'La consulta de planes'),
            }));
        return () => { active = false; };
    }, [accountAttempt, user.id]);

    // Se ejecuta solo cuando planes y cuenta terminan de cargar (loaded pasa a true),
    // no cada vez que cambia `plans` (por ejemplo tras replacePlans en choose/confirm).
    useEffect(() => {
        if (!loaded) return;
        let active = true;
        (async () => {
            const local = readPlanPreference();
            const code = readPlanIntent();
            const { selected: chosen, needsReselection } = resolvePlanSelection(plans, account.preference, local, code);
            try {
                if ((local || code) && chosen) {
                    await setPreference(chosen.version_id);
                    if (active) clearPlanPreference();
                }
            } catch (failure) {
                if (active) setNotice(serviceMessage(failure, 'La selección de planes'));
                return;
            }
            if (!active) return;
            setSelected(chosen);
            setNotice(needsReselection
                ? 'El plan elegido cambió o ya no está disponible. Revisa las condiciones y selecciona de nuevo.'
                : '');
        })();
        return () => { active = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [loaded]);

    function retry() {
        reloadPlans();
        setAccountAttempt((value) => value + 1);
    }

    async function choose(plan) {
        if (submitting.current) return;
        submitting.current = true;
        setBusy(true);
        setSelected(null);
        try {
            const result = await selectPlan(plan.version_id);
            if (result.needsReselection) {
                replacePlans(result.plans);
                setNotice('Las condiciones cambiaron. Actualizamos los planes; vuelve a elegir y confirmar.');
                return;
            }
            clearPlanPreference();
            setSelected(plan);
            setNotice('');
            navigate('/plans/summary');
        } catch (failure) {
            setNotice(serviceMessage(failure, 'La selección de planes'));
        } finally { submitting.current = false; setBusy(false); }
    }

    async function confirm() {
        if (submitting.current || !selected || account.subscription) return;
        submitting.current = true;
        setBusy(true);
        try {
            // Consulta fresca a propósito: el servidor aún no valida la versión enviada.
            const fresh = await getPlans();
            const latest = fresh.find((plan) => plan.code === selected.code);
            if (!latest || !latest.available || latest.version_id !== selected.version_id ||
                Number(latest.price) !== 0 || latest.capacity_bytes !== selected.capacity_bytes) {
                replacePlans(fresh);
                setSelected(null);
                setNotice('Las condiciones cambiaron. Vuelve a elegir y confirmar el plan.');
                return;
            }
            const response = await activateFree(selected.version_id);
            const subscription = validateSubscription(response);
            if (!subscription) throw new Error('No se pudo confirmar la activación. Consulta tu plan antes de repetirla.');
            clearPlanPreference();
            setAccount((previous) => ({ ...previous, subscription }));
            setNotice('Tu plan está activo.');
            await refresh();
        } catch (failure) {
            setNotice(serviceMessage(failure, 'La activación del plan'));
            if (failure.status === 409) retry();
        } finally { submitting.current = false; setBusy(false); }
    }

        // Contratación pagada: el servidor calcula el resumen y el pago lo ejecuta el checkout.
    async function startPaidContract() {
        if (submitting.current || !selected) return;
        submitting.current = true;
        setBusy(true);
        try {
            const quote = await createQuote('contract', selected.version_id);
            navigate(`/payments/checkout/${quote.id}`);
        } catch (failure) {
            setNotice(quoteErrorMessage(failure));
            if (failure.status === 409) retry();
        } finally { submitting.current = false; setBusy(false); }
    }

    function chooseInformational(plan) {
        setIntentError('');
        try {
            savePlanIntent(plan.code);
            setIntent(plan.code);
            navigate('/plans/summary');
        } catch { setIntentError('No se pudo guardar tu selección en el navegador.'); }
    }

    const information = summary && intent ? FALLBACK_PLANS.filter((plan) => plan.code === intent) : FALLBACK_PLANS;

    return <section className={styles.page} aria-labelledby="plans-page-title">
        <h1 id="plans-page-title">{summary ? 'Confirma tu plan' : 'Elige tu plan'}</h1>
        <p>Cuenta: {user.email}</p>
        {loading ? <p role="status">Consultando planes y suscripción…</p> : error ?
            <>
                <div role="alert"><p>{error}</p><Button onClick={retry}>Reintentar</Button></div>
                {intentError && <p role="alert">{intentError}</p>}
                <p>Estos son los planes anunciados en la landing. Son informativos: podrás confirmar las condiciones y activar un plan cuando el servicio esté disponible.</p>
                <div className={styles.grid}>{information.map((plan) => <article className={styles.card} key={plan.code}>
                    <h2>{plan.name}</h2>
                    <p>Q{plan.price}{plan.price > 0 ? ' / mes' : ''}</p>
                    <p>{formatStorage(plan.capacity_bytes)} de almacenamiento</p>
                    <p>Activación no disponible</p>
                    {!summary && <Button onClick={() => chooseInformational(plan)}>Elegir {plan.name}</Button>}
                </article>)}</div>
                {summary && <Link to="/plans">Cambiar selección</Link>}
            </> : <>
                {notice && <p role="status">{notice}</p>}
                {account.subscription ? <article className={styles.card}>
                    <h2>Tu plan actual: {account.subscription.plan.name}</h2>
                    <p>Ya tienes una suscripción. Visitar esta página no cambia tu plan.</p>
                    <Link to="/files">Ir a mis archivos</Link>
                    <Link to="/subscription">Ver mi suscripción</Link>
                </article> : summary && selected ? <article className={styles.card}>
                    <h2>{selected.name}</h2>
                    <p>{selected.price} {selected.currency}{selected.period ? ` / ${selected.period}` : ''}</p>
                    <p>{formatStorage(selected.capacity_bytes)} de almacenamiento</p>
                    <p>Revisa estas condiciones antes de confirmar. Elegir un plan no lo activa automáticamente.</p>
                    {selected.available && selected.code === 'gratis' && Number(selected.price) === 0 ?
                        <Button loading={busy} onClick={confirm}>Confirmar y activar Gratis</Button> :
                        selected.available && Number(selected.price) > 0 ?
                            <Button loading={busy} loadingLabel="Preparando pago…" onClick={startPaidContract}>Continuar al pago</Button> :
                            <p>La contratación de este plan no está disponible por el momento. Puedes elegir Gratis.</p>}
                    <Link to="/plans">Cambiar selección</Link>
                </article> : <>
                    <p>Selecciona un plan y revisa el resumen antes de activarlo.</p>
                    {plans.length === 0 && <p>No hay planes disponibles por el momento.</p>}
                    <div className={styles.grid}>{plans.map((plan) => <article className={styles.card} key={plan.version_id}>
                        <h2>{plan.name}</h2>
                        <p>{plan.price} {plan.currency}{plan.period ? ` / ${plan.period}` : ''}</p>
                        <p>{formatStorage(plan.capacity_bytes)} de almacenamiento</p>
                        {!plan.available && <p>Contratación no disponible</p>}
                        <Button disabled={busy} onClick={() => choose(plan)}>Ver resumen de {plan.name}</Button>
                    </article>)}</div>
                </>}
            </>}
        <Link to="/profile">Volver a mi perfil</Link>
        <Button variant="ghost" disabled={busy} onClick={() => navigate('/')}>
            {account.subscription ? 'Volver al inicio' : 'Salir sin confirmar'}
        </Button>
    </section>;
}