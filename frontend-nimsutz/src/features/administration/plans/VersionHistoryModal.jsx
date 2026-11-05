import { useEffect, useState } from 'react';
import { History, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { fetchPlanVersions, formatCapacity } from './adminPlansApi';
import styles from './AdminPlansPage.module.css';

export default function VersionHistoryModal({ plan, onClose }) {
    const [versions, setVersions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        let active = true;
        setLoading(true);
        setError('');

        fetchPlanVersions(plan.id)
            .then((data) => {
                if (active) {
                    setVersions(data.results || []);
                }
            })
            .catch((err) => {
                if (active) {
                    setError(err.message || 'No se pudo cargar el historial de versiones.');
                }
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, [plan.id]);

    function formatDate(dateStr) {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('es-GT', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    return (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="history-modal-title">
            <div className={styles.modalContainer}>
                <div className={styles.modalHeader}>
                    <div className={styles.modalTitleBox}>
                        <History size={20} className={styles.modalIcon} />
                        <div>
                            <h2 id="history-modal-title" className={styles.modalTitle}>
                                Historial de Versiones — {plan.name}
                            </h2>
                            <p className={styles.modalSubtitle}>
                                Código del plan: <code>{plan.code}</code> | Solo lectura
                            </p>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} className={styles.closeButton} aria-label="Cerrar modal">
                        <X size={18} />
                    </button>
                </div>

                <div className={styles.infoBanner}>
                    <p>
                        <strong>Inmutabilidad contractual:</strong> Las versiones publicadas conservan de forma permanente
                        las condiciones de precio y capacidad bajo las cuales fueron contratadas por los usuarios.
                    </p>
                </div>

                <div className={styles.modalBody}>
                    {loading && (
                        <div className={styles.loadingBox}>
                            <Loader2 size={28} className={styles.spinner} />
                            <p>Cargando historial de versiones…</p>
                        </div>
                    )}

                    {error && (
                        <div className={styles.errorBox}>
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </div>
                    )}

                    {!loading && !error && versions.length === 0 && (
                        <p className={styles.emptyText}>No hay versiones registradas para este plan.</p>
                    )}

                    {!loading && !error && versions.length > 0 && (
                        <div className={styles.tableWrapper}>
                            <table className={styles.versionTable}>
                                <thead>
                                    <tr>
                                        <th>Versión</th>
                                        <th>Nombre Comercial</th>
                                        <th>Precio</th>
                                        <th>Capacidad</th>
                                        <th>Periodicidad</th>
                                        <th>Fecha Publicación</th>
                                        <th>Estado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {versions.map((v) => (
                                        <tr key={v.id} className={v.is_current ? styles.currentVersionRow : ''}>
                                            <td className={styles.versionBadgeCell}>
                                                <span className={styles.versionBadge}>v{v.version_number}</span>
                                            </td>
                                            <td>
                                                <div className={styles.versionNameCell}>
                                                    <span className={styles.primaryText}>{v.name}</span>
                                                    {v.description && (
                                                        <span className={styles.mutedText}>{v.description}</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className={styles.priceCell}>
                                                {Number(v.price) === 0 ? 'Gratis' : `Q ${v.price}`}
                                            </td>
                                            <td>{formatCapacity(v.capacity_bytes)}</td>
                                            <td>
                                                {v.billing_period === 'calendar_month'
                                                    ? 'Mes calendario'
                                                    : 'Sin vencimiento'}
                                            </td>
                                            <td className={styles.dateCell}>{formatDate(v.created_at)}</td>
                                            <td>
                                                {v.is_current ? (
                                                    <span className={styles.activeTag}>
                                                        <CheckCircle size={14} /> Vigente
                                                    </span>
                                                ) : (
                                                    <span className={styles.archivedTag}>Histórica</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                <div className={styles.modalFooter}>
                    <button type="button" onClick={onClose} className={styles.secondaryButton}>
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    );
}
