import { useState } from 'react';
import { useAuth } from '@shared/auth/AuthContext';
import { useLocation } from 'react-router-dom';
import styles from './Layouts.module.css';

export default function Header() {
    const { user, signOut } = useAuth();
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    async function exit() {
        setBusy(true);
        try { await signOut(); setError(''); }
        catch { setError('No se pudo cerrar la sesión. Inténtalo de nuevo.'); }
        finally { setBusy(false); }
    }
    const { pathname } = useLocation();
    return (
        <header className={styles.header}>
            <span>
                {pathname === '/design-system'
                    ? 'Sistema de diseño'
                    : 'Mis archivos'}
            </span>
            {user && <button onClick={exit} disabled={busy}>Cerrar sesión</button>}
            {error && <span role="alert">{error}</span>}
        </header>
    );
}
