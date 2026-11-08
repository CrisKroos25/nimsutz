import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Button from '@shared/components/Button/Button';
import { formatStorage, formatDate } from '@shared/utils/planFormat';
import { useAdminClient } from '@features/administration/clients/hooks/useAdminClient';
import { useClientStatusChange } from '@features/administration/clients/hooks/useClientStatusChange';
import ClientStatusBadge from '@features/administration/clients/components/ClientStatusBadge';
import ClientStatusModal from '@features/administration/clients/components/ClientStatusModal';
import { ClientDetailSkeleton } from '@features/administration/clients/components/ClientsSkeleton';
import { canReactivate, canSuspend, describeChange } from '@features/administration/clients/utils/clientStatus';
import styles from '@features/administration/clients/pages/AdminClients.module.css';

function Row({ label, children }) {
    return (
        <div className={styles.row}>
            <dt>{label}</dt>
            <dd>{children}</dd>
        </div>
    );
}

export default function AdministrationClientDetailPage() {
    const { clientId } = useParams();
    const { client, loading, error, reload, retry } = useAdminClient(clientId);
    const [pendingAction, setPendingAction] = useState(null); // 'suspend' | 'reactivate' | null
    const [notice, setNotice] = useState(null);

    const handleDone = useCallback(
        (result, action) => {
            setNotice(describeChange(action, result));
            setPendingAction(null);
            reload(); // el estado mostrado siempre se vuelve a leer del servidor
        },
        [reload],
    );
    const { run, busy, error: actionError, clearError } = useClientStatusChange(clientId, handleDone);

    const openModal = (action) => {
        clearError();
        setNotice(null);
        setPendingAction(action);
    };
    const closeModal = () => {
        if (!busy) setPendingAction(null);
    };

    return (
        <section className={styles.page}>
            <Link to="/administration/clients" className={styles.backLink}>
                <ArrowLeft size={16} aria-hidden="true" />
                Volver a clientes
            </Link>

            <div aria-busy={loading}>
                {loading && <ClientDetailSkeleton />}

                {!loading && error && (
                    <div className={styles.alert} role="alert">
                        <p>{error}</p>
                        <div className={styles.actions}>
                            <Button type="button" variant="secondary" onClick={retry}>Reintentar</Button>
                        </div>
                    </div>
                )}

                {!loading && !error && client && (
                    <div className={styles.content}>
                        <header className={styles.heading}>
                            <div className={styles.cardHead}>
                                <h1>{client.name}</h1>
                                <ClientStatusBadge status={client.account_status} />
                            </div>
                            <p>{client.email}</p>
                        </header>

                        {notice && <p className={styles.notice} role="status">{notice}</p>}

                        <div className={styles.grid}>
                            <article className={styles.card}>
                                <h2>Cuenta</h2>
                                <dl className={styles.details}>
                                    <Row label="Estado"><ClientStatusBadge status={client.account_status} /></Row>
                                    <Row label="Correo verificado">{client.email_verified ? 'Sí' : 'No'}</Row>
                                    <Row label="Registrado">{formatDate(client.created_at)}</Row>
                                    <Row label="Última actualización">{formatDate(client.updated_at)}</Row>
                                </dl>
                            </article>

                            <article className={styles.card}>
                                <h2>Plan y consumo</h2>
                                <dl className={styles.details}>
                                    <Row label="Plan">{client.plan?.name ?? 'Sin plan'}</Row>
                                    {client.plan && <Row label="Versión contratada">#{client.plan.version_id}</Row>}
                                    <Row label="Vigencia hasta">{client.coverage_end ? formatDate(client.coverage_end) : '—'}</Row>
                                    <Row label="Espacio usado">{formatStorage(client.usage_bytes)}</Row>
                                    <Row label="Archivos">{client.file_count}</Row>
                                </dl>
                                <p className={styles.muted}>El consumo incluye los archivos en papelera.</p>
                            </article>
                        </div>

                        <article className={styles.card}>
                            <h2>Acceso a la cuenta</h2>
                            <p className={styles.muted}>
                                Suspender o reactivar solo cambia el acceso. Los archivos, el plan, los pagos y el
                                historial del cliente se conservan, y su contenido sigue siendo privado.
                            </p>
                            {client.account_status === 'pendiente_verificacion' && (
                                <p className={styles.warning}>
                                    Este cliente aún no verificó su correo. Reactivar una cuenta no lo verifica.
                                </p>
                            )}
                            <div className={`${styles.actions} ${styles.buttonRow}`}>
                                {canSuspend(client.account_status) && (
                                    <Button type="button" variant="danger" onClick={() => openModal('suspend')}>
                                        Suspender cuenta
                                    </Button>
                                )}
                                {canReactivate(client.account_status) && (
                                    <Button type="button" onClick={() => openModal('reactivate')}>
                                        Reactivar cuenta
                                    </Button>
                                )}
                            </div>
                        </article>
                    </div>
                )}
            </div>

            {pendingAction && client && (
                <ClientStatusModal
                    action={pendingAction}
                    client={client}
                    busy={busy}
                    error={actionError}
                    onConfirm={run}
                    onClose={closeModal}
                />
            )}
        </section>
    );
}