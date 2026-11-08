import { AlertTriangle, UserCheck } from 'lucide-react';
import Modal from '@shared/components/Modal/Modal';
import Button from '@shared/components/Button/Button';
import styles from '../pages/AdminClients.module.css';

const COPY = {
    suspend: {
        title: 'Suspender cuenta',
        icon: <AlertTriangle size={20} />,
        confirm: 'Suspender cuenta',
        loading: 'Suspendiendo...',
        variant: 'danger',
        points: [
            'Cierra las sesiones activas del cliente y le impide iniciar sesión.',
            'Si luego reactivas la cuenta, las sesiones anteriores no vuelven: tendrá que iniciar sesión de nuevo.',
            'Sus archivos, plan, pagos e historial se conservan. No se borra nada.',
        ],
    },
    reactivate: {
        title: 'Reactivar cuenta',
        icon: <UserCheck size={20} />,
        confirm: 'Reactivar cuenta',
        loading: 'Reactivando...',
        variant: 'primary',
        points: [
            'Si el cliente aún no verificó su correo, la cuenta seguirá pendiente de verificación y no podrá ingresar.',
            'No restaura sesiones anteriores, no cambia su plan ni recupera cobertura vencida.',
            'Sus archivos e historial no se modifican.',
        ],
    },
};

export default function ClientStatusModal({ action, client, busy, error, onConfirm, onClose }) {
    const copy = COPY[action];
    return (
        <Modal open onClose={() => !busy && onClose()} title={copy.title} icon={copy.icon}>
            <div className={styles.modalBody}>
                <p>
                    Vas a {action === 'suspend' ? 'suspender' : 'reactivar'} la cuenta de{' '}
                    <strong>{client.name}</strong> ({client.email}).
                </p>
                <ul className={styles.modalList}>
                    {copy.points.map((point) => <li key={point}>{point}</li>)}
                </ul>
                {error && <p className={styles.alert} role="alert">{error}</p>}
                <div className={styles.modalActions}>
                    <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
                        Cancelar
                    </Button>
                    <Button
                        type="button"
                        variant={copy.variant}
                        onClick={() => onConfirm(action)}
                        loading={busy}
                        loadingLabel={copy.loading}
                    >
                        {copy.confirm}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}