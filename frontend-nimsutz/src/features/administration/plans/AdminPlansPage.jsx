import { useEffect, useState, useCallback } from 'react';
import { Layers, Plus, History, PowerOff, CheckCircle2, XCircle, RefreshCw, Loader2, AlertCircle } from 'lucide-react';
import { fetchAdminPlans, formatCapacity } from './adminPlansApi';
import VersionHistoryModal from './VersionHistoryModal';
import PublishVersionModal from './PublishVersionModal';
import DeactivatePlanModal from './DeactivatePlanModal';
import styles from './AdminPlansPage.module.css';

export default function AdminPlansPage() {
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'active', 'inactive'

    // Modales
    const [historyPlan, setHistoryPlan] = useState(null);
    const [publishPlan, setPublishPlan] = useState(null);
    const [deactivateTarget, setDeactivateTarget] = useState(null);

    const loadPlans = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            let filterVal = null;
            if (activeFilter === 'active') filterVal = true;
            if (activeFilter === 'inactive') filterVal = false;

            const data = await fetchAdminPlans({ active: filterVal });
            setPlans(data.results || []);
        } catch (err) {
            setError(err.message || 'No se pudo cargar el catálogo de planes.');
        } finally {
            setLoading(false);
        }
    }, [activeFilter]);

    useEffect(() => {
        loadPlans();
    }, [loadPlans]);

    return (
        <main className={styles.container}>
            <header className={styles.pageHeader}>
                <div className={styles.titleArea}>
                    <h1 className={styles.pageTitle}>Administración de Catálogo</h1>
                    <p className={styles.pageSubtitle}>
                        Control de condiciones comerciales, historial de versiones inmutables y disponibilidad de planes.
                    </p>
                </div>

                <div className={styles.filterBar} role="group" aria-label="Filtrar planes por estado">
                    <button
                        type="button"
                        className={`${styles.filterPill} ${activeFilter === 'all' ? styles.activeFilterPill : ''}`}
                        onClick={() => setActiveFilter('all')}
                    >
                        Todos ({plans.length})
                    </button>
                    <button
                        type="button"
                        className={`${styles.filterPill} ${activeFilter === 'active' ? styles.activeFilterPill : ''}`}
                        onClick={() => setActiveFilter('active')}
                    >
                        Disponibles
                    </button>
                    <button
                        type="button"
                        className={`${styles.filterPill} ${activeFilter === 'inactive' ? styles.activeFilterPill : ''}`}
                        onClick={() => setActiveFilter('inactive')}
                    >
                        Desactivados
                    </button>
                </div>
            </header>

            {error && (
                <div className={styles.errorBox}>
                    <AlertCircle size={20} />
                    <span>{error}</span>
                    <button type="button" onClick={loadPlans} className={styles.reloadButton}>
                        <RefreshCw size={14} /> Reintentar
                    </button>
                </div>
            )}

            {loading && (
                <div className={styles.loadingBox}>
                    <Loader2 size={32} className={styles.spinner} />
                    <p>Consultando catálogo de planes…</p>
                </div>
            )}

            {!loading && !error && plans.length === 0 && (
                <p className={styles.emptyText}>No se encontraron planes con el filtro seleccionado.</p>
            )}

            {!loading && !error && plans.length > 0 && (
                <section className={styles.plansGrid} aria-label="Lista de planes administrables">
                    {plans.map((plan) => {
                        const cv = plan.current_version;
                        const isFree = plan.code === 'free';

                        return (
                            <article
                                key={plan.id}
                                className={`${styles.planCard} ${!plan.active ? styles.planCardInactive : ''}`}
                            >
                                <div>
                                    <div className={styles.planCardHeader}>
                                        <div>
                                            <h2 className={styles.planName}>{plan.name}</h2>
                                            <span className={styles.planCode}>{plan.code}</span>
                                        </div>
                                        <div className={styles.planBadges}>
                                            {plan.active ? (
                                                <span className={styles.badgeActive}>
                                                    <CheckCircle2 size={13} /> Disponible
                                                </span>
                                            ) : (
                                                <span className={styles.badgeInactive}>
                                                    <XCircle size={13} /> Desactivado
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <p className={styles.planDescription}>
                                        {plan.description || 'Sin descripción comercial especificada.'}
                                    </p>

                                    <div className={styles.planDetailsBox}>
                                        <div className={styles.detailItem}>
                                            <span className={styles.detailLabel}>Versión vigente</span>
                                            <span className={styles.detailValue}>
                                                v{cv ? cv.version_number : 1}
                                            </span>
                                            <span className={styles.versionCountTag}>
                                                <History size={12} /> {plan.versions_count}{' '}
                                                {plan.versions_count === 1 ? 'versión' : 'versiones'}
                                            </span>
                                        </div>

                                        <div className={styles.detailItem}>
                                            <span className={styles.detailLabel}>Precio</span>
                                            <span className={styles.detailValue}>
                                                {cv && Number(cv.price) === 0 ? 'Gratis' : `Q ${cv?.price || '0.00'}`}
                                            </span>
                                            <span className={styles.helperText}>
                                                {isFree ? 'Sin vencimiento' : 'Por mes'}
                                            </span>
                                        </div>

                                        <div className={styles.detailItem}>
                                            <span className={styles.detailLabel}>Almacenamiento</span>
                                            <span className={styles.detailValue}>
                                                {cv ? formatCapacity(cv.capacity_bytes) : '—'}
                                            </span>
                                        </div>

                                        <div className={styles.detailItem}>
                                            <span className={styles.detailLabel}>Periodicidad</span>
                                            <span className={styles.detailValue}>
                                                {cv?.billing_period === 'calendar_month'
                                                    ? 'Mes calendario'
                                                    : 'Sin cobro'}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <footer className={styles.cardActions}>
                                    <div className={styles.buttonRow}>
                                        <button
                                            type="button"
                                            onClick={() => setHistoryPlan(plan)}
                                            className={styles.secondaryButton}
                                            title="Consultar historial inmutable de versiones"
                                        >
                                            <History size={16} /> Historial
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setPublishPlan(plan)}
                                            className={styles.primaryButton}
                                            title="Publicar una nueva versión con nuevas condiciones"
                                        >
                                            <Plus size={16} /> Nueva versión
                                        </button>
                                    </div>

                                    {plan.active && !isFree && (
                                        <button
                                            type="button"
                                            onClick={() => setDeactivateTarget(plan)}
                                            className={styles.dangerOutlineButton}
                                            title="Desactivar plan para nuevas contrataciones"
                                        >
                                            <PowerOff size={14} /> Desactivar plan comercial
                                        </button>
                                    )}
                                </footer>
                            </article>
                        );
                    })}
                </section>
            )}

            {/* Modales */}
            {historyPlan && (
                <VersionHistoryModal plan={historyPlan} onClose={() => setHistoryPlan(null)} />
            )}

            {publishPlan && (
                <PublishVersionModal
                    plan={publishPlan}
                    onClose={() => setPublishPlan(null)}
                    onSuccess={() => {
                        setPublishPlan(null);
                        loadPlans();
                    }}
                    onReloadRequired={loadPlans}
                />
            )}

            {deactivateTarget && (
                <DeactivatePlanModal
                    plan={deactivateTarget}
                    onClose={() => setDeactivateTarget(null)}
                    onSuccess={() => {
                        setDeactivateTarget(null);
                        loadPlans();
                    }}
                />
            )}
        </main>
    );
}

