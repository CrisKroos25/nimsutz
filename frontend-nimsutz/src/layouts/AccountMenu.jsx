import { useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, LogOut, UserRound } from 'lucide-react';
import { useAuth } from '@shared/auth/AuthContext';
import { getAccountIdentity } from '@shared/auth/accountIdentity';
import styles from './AccountMenu.module.css';

export default function AccountMenu() {
    const { user, signOut } = useAuth();
    const { name, initial, email } = getAccountIdentity(user);
    const [open, setOpen] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const root = useRef(null);
    const trigger = useRef(null);
    const panelId = useId();

    useEffect(() => {
        if (!open) return;
        function dismiss(event) {
            if (!root.current?.contains(event.target)) setOpen(false);
        }
        function escape(event) {
            if (event.key === 'Escape') {
                setOpen(false);
                trigger.current?.focus();
            }
        }
        document.addEventListener('pointerdown', dismiss);
        document.addEventListener('keydown', escape);
        return () => {
            document.removeEventListener('pointerdown', dismiss);
            document.removeEventListener('keydown', escape);
        };
    }, [open]);

    async function exit() {
        setBusy(true);
        setError('');
        try {
            await signOut();
        } catch {
            setError('No se pudo cerrar la sesión. Inténtalo de nuevo.');
        } finally {
            setBusy(false);
        }
    }

    return (
        <div ref={root} className={styles.account} onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
        }}>
            <button ref={trigger} type="button" className={styles.trigger}
                aria-label={`Cuenta de ${name}`} aria-expanded={open}
                aria-controls={open ? panelId : undefined} onClick={() => setOpen(!open)}>
                <span className={styles.avatar} aria-hidden="true">{initial}</span>
                <span className={styles.name}>{name}</span>
                <ChevronDown size={16} aria-hidden="true" />
            </button>
            {open && (
                <div id={panelId} className={styles.panel}>
                    <div className={styles.identity}>
                        <strong>{name}</strong>
                        <span>{email}</span>
                    </div>
                    <nav aria-label="Opciones de cuenta">
                        <Link to="/profile" onClick={() => setOpen(false)}>
                            <UserRound size={18} aria-hidden="true" /> Mi perfil
                        </Link>
                        <button type="button" onClick={exit} disabled={busy} aria-busy={busy}>
                            <LogOut size={18} aria-hidden="true" />
                            {busy ? 'Cerrando sesión…' : 'Cerrar sesión'}
                        </button>
                    </nav>
                    {error && <p role="alert" className={styles.error}>{error}</p>}
                </div>
            )}
        </div>
    );
}
