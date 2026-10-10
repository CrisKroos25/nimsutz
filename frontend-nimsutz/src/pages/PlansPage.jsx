import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import { readPlanPreference, readPlanIntent, savePlanIntent, clearPlanPreference } from '@shared/auth/accessFlow';
import { getPlans, getPreference, setPreference, getSubscription, validateSubscription, activateFree, serviceMessage } from '@shared/api/accountApi';
import Button from '@shared/components/Button/Button';
import { PLAN_INFORMATION } from '@shared/planInformation';
import styles from './PlansPage.module.css';

export default function PlansPage() {
    const { user, refresh } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [state, setState] = useState({ loading: true, plans: [], subscription: null, selected: null, error: '', notice: '' });
    const [attempt, setAttempt] = useState(0);
    const [busy, setBusy] = useState(false);
    const [intent, setIntent] = useState(readPlanIntent);
    const submitting = useRef(false);
    const summary = location.pathname.endsWith('/summary');

    useEffect(() => {
        let active = true;
        async function load() {
            try {
                const [plans, current, preference] = await Promise.all([getPlans(), getSubscription(), getPreference()]);
                const subscription = validateSubscription(current);
                const local = readPlanPreference();
                const code = readPlanIntent();
                const version = local || preference?.preferred_plan_version_id;
                const selected = !local && !code && preference.is_current === false ? null :
                    plans.find((plan) => code ? plan.code === code : String(plan.version_id) === String(version)) || null;
                if ((local || code) && selected && active) {
                    await setPreference(selected.version_id);
                    if (active) clearPlanPreference();
                }
                if (active) setState({ loading: false, plans, subscription, selected, error: '',
                    notice: (version || code) && !selected ? 'El plan elegido cambió o ya no está disponible. Revisa las condiciones y selecciona de nuevo.' : '' });
            } catch (failure) {
                if (active) setState({ loading: false, plans: [], subscription: null, selected: null,
                    error: serviceMessage(failure, 'La consulta de planes'), notice: '' });
            }
        }
        load();
        return () => { active = false; };
    }, [attempt, user.id]);

    async function choose(plan) {
        if (submitting.current) return;
        submitting.current = true;
        setBusy(true);
        try {
            await setPreference(plan.version_id);
            clearPlanPreference();
            setState((previous) => ({ ...previous, selected: plan, notice: '', error: '' }));
            navigate('/plans/summary');
        } catch (failure) {
            setState((previous) => ({ ...previous, notice: serviceMessage(failure, 'La selección de planes') }));
        } finally { submitting.current = false; setBusy(false); }
    }

    async function confirm() {
        if (submitting.current || !state.selected || state.subscription) return;
        submitting.current = true;
        setBusy(true);
        try {
            // Reconsultamos las condiciones; el servidor aún no valida la versión enviada.
            const plans = await getPlans();
            const latest = plans.find((plan) => plan.code === state.selected.code);
            if (!latest || !latest.available || latest.version_id !== state.selected.version_id ||
                Number(latest.price) !== 0 || latest.capacity_bytes !== state.selected.capacity_bytes) {
                setState((previous) => ({ ...previous, plans, selected: null, notice: 'Las condiciones cambiaron. Vuelve a elegir y confirmar el plan.' }));
                return;
            }
            const response = await activateFree(state.selected.version_id);
            const subscription = validateSubscription(response);
            if (!subscription) throw new Error('No se pudo confirmar la activación. Consulta tu plan antes de repetirla.');
            clearPlanPreference();
            setState((previous) => ({ ...previous, subscription, notice: 'Tu plan está activo.' }));
            await refresh();
        } catch (failure) {
            setState((previous) => ({ ...previous, notice: serviceMessage(failure, 'La activación del plan') }));
            if (failure.status === 409) {
                setState((previous) => ({ ...previous, loading: true }));
                setAttempt((value) => value + 1);
            }
        } finally { submitting.current = false; setBusy(false); }
    }

    function retry() {
        setState((previous) => ({ ...previous, loading: true }));
        setAttempt((value) => value + 1);
    }
    const selected = state.selected;
    const information = summary && intent ? PLAN_INFORMATION.filter((plan) => plan.code === intent) : PLAN_INFORMATION;
    return <section className={styles.page} aria-labelledby="plans-page-title">
        <h1 id="plans-page-title">{summary ? 'Confirma tu plan' : 'Elige tu plan'}</h1>
        <p>Cuenta: {user.email}</p>
        {state.loading ? <p role="status">Consultando planes y suscripción…</p> : state.error ?
            <>
                <div role="alert"><p>{state.error}</p><Button onClick={retry}>Reintentar</Button></div>
                <p>Estos son los planes anunciados en la landing. Son informativos: podrás confirmar las condiciones y activar un plan cuando el servicio esté disponible.</p>
                <div className={styles.grid}>{information.map((plan) => <article className={styles.card} key={plan.code}>
                    <h2>{plan.name}</h2><p>Q{plan.price}{plan.price > 0 ? ' / mes' : ''}</p>
                    <p>{plan.storage} de almacenamiento</p>
                    <p>Activación no disponible</p>
                    {!summary && <Button onClick={() => {
                        try { savePlanIntent(plan.code); setIntent(plan.code); navigate('/plans/summary'); }
                        catch { setState((previous) => ({ ...previous, error: 'No se pudo guardar tu selección en el navegador.' })); }
                    }}>Elegir {plan.name}</Button>}
                </article>)}</div>
                {summary && <Link to="/plans">Cambiar selección</Link>}
            </> : <>
                {state.notice && <p role="status">{state.notice}</p>}
                {state.subscription ? <article className={styles.card}>
                    <h2>Tu plan actual: {state.subscription.plan.name}</h2>
                    <p>Ya tienes una suscripción. Visitar esta página no cambia tu plan.</p>
                    <Link to="/files">Ir a mis archivos</Link>
                </article> : summary && selected ? <article className={styles.card}>
                    <h2>{selected.name}</h2>
                    <p>{selected.price} {selected.currency}{selected.period ? ` / ${selected.period}` : ''}</p>
                    <p>{Math.round(selected.capacity_bytes / 1024 / 1024)} MB de almacenamiento</p>
                    <p>Revisa estas condiciones antes de confirmar. Elegir un plan no lo activa automáticamente.</p>
                    {selected.available && selected.code === 'gratis' && Number(selected.price) === 0 ?
                        <Button loading={busy} onClick={confirm}>Confirmar y activar Gratis</Button> :
                        <p>La contratación de este plan no está disponible por el momento. Puedes elegir Gratis.</p>}
                    <Link to="/plans">Cambiar selección</Link>
                </article> : <>
                    <p>Selecciona un plan y revisa el resumen antes de activarlo.</p>
                    {state.plans.length === 0 && <p>No hay planes disponibles por el momento.</p>}
                    <div className={styles.grid}>{state.plans.map((plan) => <article className={styles.card} key={plan.version_id}>
                        <h2>{plan.name}</h2>
                        <p>{plan.price} {plan.currency}{plan.period ? ` / ${plan.period}` : ''}</p>
                        <p>{Math.round(plan.capacity_bytes / 1024 / 1024)} MB de almacenamiento</p>
                        {!plan.available && <p>Contratación no disponible</p>}
                        <Button disabled={busy} onClick={() => choose(plan)}>Ver resumen de {plan.name}</Button>
                    </article>)}</div>
                </>}
            </>}
        <Link to="/profile">Volver a mi perfil</Link>
        <Button variant="ghost" disabled={busy} onClick={() => navigate('/')}>
            {state.subscription ? 'Volver al inicio' : 'Salir sin confirmar'}
        </Button>
    </section>;
}
