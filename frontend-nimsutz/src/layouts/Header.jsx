import { useAuth } from '@shared/auth/AuthContext';
import { useLocation } from 'react-router-dom';
import AccountMenu from './AccountMenu';
import styles from './Layouts.module.css';

export default function Header() {
    const { user } = useAuth();
    const { pathname } = useLocation();
    const title = pathname.startsWith('/profile')
        ? 'Mi perfil'
        : pathname.startsWith('/trash') ? 'Papelera' : 'Mis archivos';

    return (
        <header className={styles.header}>
            <span>{title}</span>
            {user && <AccountMenu key={user.id} />}
        </header>
    );
}
