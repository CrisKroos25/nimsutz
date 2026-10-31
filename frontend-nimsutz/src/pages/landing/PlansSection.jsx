import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import { savePlanIntent } from '@shared/auth/accessFlow';
import { usePlans } from '@shared/hooks/usePlans';
import { formatStorage, formatPrice } from '@shared/utils/planFormat';
import { FALLBACK_PLANS } from '@shared/planInformation';
import { Check } from 'lucide-react';
import Button from '../../shared/components/Button/Button';
import styles from './Information.module.css';

const FEATURES = [
    'Cargar archivos',
    'Descargar tus documentos',
    'Organizar en carpetas',
    'Renombrar y mover archivos',
];

export default function PlansSection() {
    const { plans, loading: plansLoading, error: plansError, reload } = usePlans();
    const [selectedPlan, setSelectedPlan] = useState(null);
    const [error, setError] = useState('');
    const navigate = useNavigate();
    const { user, loading } = useAuth();

    // Si el backend falla, se muestra el respaldo informativo (misma forma que un plan normalizado).
    const usingFallback = Boolean(plansError);
    const displayPlans = usingFallback ? FALLBACK_PLANS : plans;

    function select(plan) {
        setError('');
        try {
            savePlanIntent(plan.code);
            setSelectedPlan(plan.code);
            navigate(user ? '/plans/summary' : '/register');
        } catch { setError('No se pudo guardar tu selección. Permite el almacenamiento del navegador e inténtalo de nuevo.'); }
    }

    return (
        <section
            id="plans"
            className={styles.section}
            aria-labelledby="plans-title"
            data-reveal="left"
        >
            <p className={styles.eyebrow}>UN ESPACIO A TU MEDIDA</p>
            <h2 id="plans-title">Elige el espacio para tus ideas</h2>
            <p>Tus documentos, organizados. Encuentra el plan que va contigo.</p>
            {error && <p role="alert">{error}</p>}
            {plansLoading && <p role="status">Cargando planes…</p>}
            {plansError && (
                <div role="alert">
                    <p>{plansError} Mostramos la información general de los planes.</p>
                    <Button variant="secondary" onClick={reload}>Reintentar</Button>
                </div>
            )}
            {!plansLoading && (
                <div className={styles.plans}>
                    {displayPlans.map((plan) => {
                        // Con datos reales, solo se puede elegir lo contratable.
                        // Con el respaldo, se permite guardar la intención para no cortar el flujo de registro.
                        const canSelect = usingFallback || plan.available;
                        const isSelected = selectedPlan === plan.code;
                        return (
                            <article
                                className={styles.plan}
                                data-selected={isSelected}
                                key={plan.code}
                            >
                                <div className={styles.planHeading}>
                                    <div className={styles.planTitle}>
                                        <h3>{plan.name}</h3>
                                        {isSelected && (
                                            <span className={styles.selectedLabel}><Check size={14} aria-hidden="true" /> Seleccionado</span>
                                        )}
                                    </div>
                                    <p className={styles.price}>
                                        <span className={styles.currency}>Q</span>
                                        <strong>{formatPrice(plan.price)}</strong>
                                        {Number(plan.price) > 0 && <span className={styles.period}>/ mes</span>}
                                    </p>
                                    <p className={styles.storage}>
                                        <strong>{formatStorage(plan.capacity_bytes)}</strong> de almacenamiento
                                    </p>
                                </div>
                                <ul className={styles.featureList}>
                                    {FEATURES.map((feature) => (
                                        <li key={feature}>
                                            <Check size={18} aria-hidden="true" />
                                            <span>{feature}</span>
                                        </li>
                                    ))}
                                </ul>
                                <Button
                                    className={styles.planAction}
                                    variant={isSelected ? 'primary' : 'secondary'}
                                    aria-label={(canSelect ? 'Seleccionar plan ' : 'Próximamente: plan ') + plan.name}
                                    aria-pressed={isSelected}
                                    disabled={loading || !canSelect}
                                    onClick={() => select(plan)}
                                >
                                    {canSelect ? 'Seleccionar plan' : 'Próximamente'}
                                </Button>
                            </article>
                        );
                    })}
                </div>
            )}
        </section>
    );
}