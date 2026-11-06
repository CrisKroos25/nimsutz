import { useState } from 'react';
import { PowerOff, X, AlertTriangle, AlertCircle, Loader2 } from 'lucide-react';
import { deactivatePlan } from './adminPlansApi';
import styles from './AdminPlansPage.module.css';

export default function DeactivatePlanModal({ plan, onClose, onSuccess }) {
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    async function handleConfirm() {
        setSubmitting(true);
        setError('');

        try {
            await deactivatePlan(plan.id);
            onSuccess();
        } catch (err) {
            setError(err.message || 'No se pudo desactivar el plan.');
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="deactivate-modal-title">
            <div className={`${styles.modalContainer} ${styles.modalSmall}`}>
                <div className={styles.modalHeader}>
                    <div className={styles.modalTitleBox}>
                        <PowerOff size={20} className={styles.dangerIcon} />
                        <div>
                            <h2 id="deactivate-modal-title" className={styles.modalTitle}>
                                Desactivar {plan.name}
                            </h2>
                            <p className={styles.modalSubtitle}>Código: {plan.code}</p>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} className={styles.closeButton} aria-label="Cerrar modal">
                        <X size={18} />
                    </button>
                </div>

                <div className={styles.modalBody}>
                    <div className={styles.warningBanner}>
                        <AlertTriangle size={20} className={styles.warningIcon} />
                        <div>
                            <p className={styles.warningTitle}>Efectos de la desactivación comercial:</p>
                            <ul className={styles.impactList}>
                                <li>
                                    <strong>Nuevos contratos:</strong> El plan dejará de aparecer en la pantalla pública de
                                    planes y no podrá ser elegido por nuevos clientes ni para mejoras de plan.
                                </li>
                                <li>
                                    <strong>Clientes existentes:</strong> Los clientes que actualmente tienen contratado
                                    este plan <u>mantienen intacta su cobertura</u> y podrán seguir renovando su versión
                                    normalmente.
                                </li>
                                <li>
                                    <strong>Preservación:</strong> No se elimina ningún dato ni versión histórica.
                                </li>
                            </ul>
                        </div>
                    </div>

                    {error && (
                        <div className={styles.errorBox}>
                            <AlertCircle size={18} />
                            <span>{error}</span>
                        </div>
                    )}
                </div>

                <div className={styles.modalFooter}>
                    <button type="button" onClick={onClose} className={styles.secondaryButton} disabled={submitting}>
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        className={styles.dangerButton}
                        disabled={submitting}
                    >
                        {submitting ? (
                            <>
                                <Loader2 size={16} className={styles.spinner} />
                                Desactivando…
                            </>
                        ) : (
                            'Confirmar desactivación'
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

