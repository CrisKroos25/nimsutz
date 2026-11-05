import { useState } from 'react';
import { PlusCircle, X, AlertTriangle, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import { publishPlanVersion, parseCapacityToBytes, formatCapacity } from './adminPlansApi';
import styles from './AdminPlansPage.module.css';

export default function PublishVersionModal({ plan, onClose, onSuccess, onReloadRequired }) {
    const isFree = plan.code === 'free';
    const currentVersion = plan.current_version;

    // Determinar valores iniciales
    const currentBytes = currentVersion?.capacity_bytes || 104857600;
    const initialUnit = currentBytes >= 1024 * 1024 * 1024 ? 'GB' : 'MB';
    const initialValue =
        initialUnit === 'GB'
            ? (currentBytes / (1024 * 1024 * 1024)).toFixed(0)
            : (currentBytes / (1024 * 1024)).toFixed(0);

    const [name, setName] = useState(currentVersion?.name || plan.name);
    const [description, setDescription] = useState(currentVersion?.description || plan.description || '');
    const [price, setPrice] = useState(isFree ? '0.00' : currentVersion?.price || '15.00');
    const [capacityVal, setCapacityVal] = useState(initialValue);
    const [capacityUnit, setCapacityUnit] = useState(initialUnit);
    const [billingPeriod] = useState(isFree ? '' : 'calendar_month');

    const [submitting, setSubmitting] = useState(false);
    const [generalError, setGeneralError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});
    const [concurrencyConflict, setConcurrencyConflict] = useState(false);

    const computedBytes = parseCapacityToBytes(capacityVal, capacityUnit);
    const nextVersionNumber = (currentVersion?.version_number || 1) + 1;

    async function handleSubmit(e) {
        e.preventDefault();
        setGeneralError('');
        setFieldErrors({});
        setConcurrencyConflict(false);

        // Validaciones en cliente
        const clientErrors = {};
        if (!name.trim()) {
            clientErrors.name = 'El nombre comercial es obligatorio.';
        }
        if (computedBytes <= 0) {
            clientErrors.capacity = 'La capacidad debe ser un número positivo.';
        }
        if (!isFree && (isNaN(Number(price)) || Number(price) <= 0)) {
            clientErrors.price = 'El precio debe ser un número mayor a 0.00.';
        }

        if (Object.keys(clientErrors).length > 0) {
            setFieldErrors(clientErrors);
            return;
        }

        setSubmitting(true);
        try {
            const payload = {
                base_version_id: currentVersion?.id,
                name: name.trim(),
                description: description.trim(),
                price: isFree ? '0.00' : price,
                capacity_bytes: computedBytes,
                billing_period: isFree ? null : 'calendar_month',
            };

            await publishPlanVersion(plan.id, payload);
            onSuccess();
        } catch (err) {
            if (err.status === 409 || err.code === 'plan_conditions_changed') {
                setConcurrencyConflict(true);
                setGeneralError(
                    'Conflicto de concurrencia: Otro administrador ha publicado una nueva versión de este plan mientras editabas. Para prevenir sobreescrituras accidentales, debes recargar las condiciones vigentes antes de publicar.',
                );
            } else {
                setGeneralError(err.message || 'Error al publicar la versión.');
                if (err.fieldErrors) {
                    setFieldErrors(err.fieldErrors);
                }
            }
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="publish-modal-title">
            <div className={styles.modalContainer}>
                <div className={styles.modalHeader}>
                    <div className={styles.modalTitleBox}>
                        <PlusCircle size={20} className={styles.modalIcon} />
                        <div>
                            <h2 id="publish-modal-title" className={styles.modalTitle}>
                                Publicar Nueva Versión — {plan.name}
                            </h2>
                            <p className={styles.modalSubtitle}>
                                Se generará la versión <strong>v{nextVersionNumber}</strong> basada en v{currentVersion?.version_number || 1}
                            </p>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} className={styles.closeButton} aria-label="Cerrar modal">
                        <X size={18} />
                    </button>
                </div>

                <div className={styles.warningBanner}>
                    <AlertTriangle size={18} className={styles.warningIcon} />
                    <p>
                        <strong>Impacto comercial:</strong> Esta nueva versión se ofrecerá a las nuevas contrataciones y
                        cambios de plan. Los contratos existentes y renovaciones continuarán respetando las condiciones de la
                        versión que cada cliente contrató originalmente.
                    </p>
                </div>

                {concurrencyConflict && (
                    <div className={styles.conflictBanner}>
                        <AlertCircle size={20} />
                        <div>
                            <p className={styles.conflictText}>{generalError}</p>
                            <button
                                type="button"
                                onClick={() => {
                                    onClose();
                                    onReloadRequired();
                                }}
                                className={styles.reloadButton}
                            >
                                <RefreshCw size={15} /> Recargar catálogo ahora
                            </button>
                        </div>
                    </div>
                )}

                {generalError && !concurrencyConflict && (
                    <div className={styles.errorBox}>
                        <AlertCircle size={18} />
                        <span>{generalError}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className={styles.modalBody}>
                    <div className={styles.formGroup}>
                        <label htmlFor="version-name" className={styles.formLabel}>
                            Nombre comercial de la versión <span className={styles.required}>*</span>
                        </label>
                        <input
                            id="version-name"
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className={`${styles.formInput} ${fieldErrors.name ? styles.inputError : ''}`}
                            placeholder="Ej. Básico Plus 2026"
                            disabled={submitting || concurrencyConflict}
                        />
                        {fieldErrors.name && <span className={styles.fieldError}>{fieldErrors.name}</span>}
                    </div>

                    <div className={styles.formGroup}>
                        <label htmlFor="version-desc" className={styles.formLabel}>
                            Descripción u oferta comercial
                        </label>
                        <textarea
                            id="version-desc"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                            className={styles.formTextarea}
                            placeholder="Describe los beneficios y características de esta versión…"
                            disabled={submitting || concurrencyConflict}
                        />
                    </div>

                    <div className={styles.formRow}>
                        <div className={styles.formGroup}>
                            <label htmlFor="version-price" className={styles.formLabel}>
                                Precio mensual (GTQ) <span className={styles.required}>*</span>
                            </label>
                            <input
                                id="version-price"
                                type="number"
                                step="0.01"
                                min="0"
                                value={price}
                                onChange={(e) => setPrice(e.target.value)}
                                className={`${styles.formInput} ${fieldErrors.price ? styles.inputError : ''}`}
                                disabled={isFree || submitting || concurrencyConflict}
                            />
                            {isFree ? (
                                <span className={styles.helperText}>El plan gratuito siempre tiene precio Q 0.00.</span>
                            ) : (
                                fieldErrors.price && <span className={styles.fieldError}>{fieldErrors.price}</span>
                            )}
                        </div>

                        <div className={styles.formGroup}>
                            <label className={styles.formLabel}>
                                Capacidad de almacenamiento <span className={styles.required}>*</span>
                            </label>
                            <div className={styles.capacityInputGroup}>
                                <input
                                    type="number"
                                    min="1"
                                    step="any"
                                    value={capacityVal}
                                    onChange={(e) => setCapacityVal(e.target.value)}
                                    className={`${styles.formInput} ${fieldErrors.capacity ? styles.inputError : ''}`}
                                    disabled={submitting || concurrencyConflict}
                                />
                                <select
                                    value={capacityUnit}
                                    onChange={(e) => setCapacityUnit(e.target.value)}
                                    className={styles.formSelect}
                                    disabled={submitting || concurrencyConflict}
                                    aria-label="Unidad de capacidad"
                                >
                                    <option value="MB">MB</option>
                                    <option value="GB">GB</option>
                                </select>
                            </div>
                            <span className={styles.helperText}>
                                Total: {formatCapacity(computedBytes)} ({computedBytes.toLocaleString()} bytes)
                            </span>
                            {fieldErrors.capacity && (
                                <span className={styles.fieldError}>{fieldErrors.capacity}</span>
                            )}
                        </div>
                    </div>

                    <div className={styles.formGroup}>
                        <label className={styles.formLabel}>Periodicidad de facturación</label>
                        <input
                            type="text"
                            value={isFree ? 'Sin vencimiento (Gratis)' : 'Mes calendario (calendar_month)'}
                            disabled
                            className={`${styles.formInput} ${styles.disabledInput}`}
                        />
                    </div>

                    <div className={styles.modalFooter}>
                        <button
                            type="button"
                            onClick={onClose}
                            className={styles.secondaryButton}
                            disabled={submitting}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className={styles.primaryButton}
                            disabled={submitting || concurrencyConflict}
                        >
                            {submitting ? (
                                <>
                                    <Loader2 size={16} className={styles.spinner} />
                                    Publicando…
                                </>
                            ) : (
                                'Confirmar y publicar versión'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

