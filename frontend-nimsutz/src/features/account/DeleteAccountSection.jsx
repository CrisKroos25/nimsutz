import { useRef, useState } from 'react';
import { TriangleAlert } from 'lucide-react';
import { useAuth } from '@shared/auth/AuthContext';
import Button from '@shared/components/Button/Button';
import Modal from '@shared/components/Modal/Modal';
import styles from './DeleteAccountSection.module.css';

export default function DeleteAccountSection() {
    const { removeAccount } = useAuth();
    const [open, setOpen] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const working = useRef(false);

    function close() {
        if (!working.current) setOpen(false);
    }

    async function confirm() {
        if (working.current) return;
        working.current = true;
        setBusy(true);
        setError('');
        try {
            await removeAccount();
        } catch (failure) {
            setError(failure.status ? failure.message
                : 'No pudimos confirmar la eliminación. Revisa tu conexión y vuelve a consultar tu cuenta antes de intentarlo de nuevo.');
            working.current = false;
            setBusy(false);
        }
    }

    return <section className={styles.section} aria-labelledby="delete-account-title">
        <h2 id="delete-account-title">Eliminar cuenta</h2>
        <p>Elimina permanentemente tu cuenta y sus datos. Esta acción no se puede deshacer.</p>
        <Button variant="danger" onClick={() => { setError(''); setOpen(true); }}>Eliminar cuenta</Button>
        <Modal open={open} onClose={close} title="¿Eliminar tu cuenta?"
            icon={<TriangleAlert aria-hidden="true" />}
            description="Tu cuenta se eliminará de forma permanente. Se borrarán tu perfil, archivos y carpetas (incluida la papelera), suscripción e historial de pagos. Esta acción no se puede deshacer.">
            <p>Podrás volver a registrarte con el mismo correo, pero empezarás desde cero. ¿Deseas continuar?</p>
            {error && <p className={styles.error} role="alert">{error}</p>}
            <div className={styles.actions}>
                <Button variant="secondary" disabled={busy} onClick={close}>Cancelar</Button>
                <Button variant="danger" loading={busy} loadingLabel="Eliminando cuenta…" onClick={confirm}>Aceptar y eliminar cuenta</Button>
            </div>
        </Modal>
    </section>;
}
