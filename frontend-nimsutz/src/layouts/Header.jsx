import { useAuth } from '@shared/auth/AuthContext';
import { useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import AccountMenu from './AccountMenu';
import styles from './Layouts.module.css';

export default function Header({ theme, toggleTheme }) {
    const { user } = useAuth();
    const { pathname } = useLocation();
    const title = pathname.startsWith('/profile')
        ? 'Mi perfil'
        : pathname.startsWith('/payments/checkout') ? 'Confirma tu plan'
        : pathname.startsWith('/payments/result') ? 'Resultado del pago'
        : pathname.startsWith('/payments/history') ? 'Historial de pagos'
        : pathname.startsWith('/subscription') ? 'Mi suscripción'
        : pathname.startsWith('/plans') ? 'Planes'
        : pathname.startsWith('/trash') ? 'Papelera' : 'Mis archivos';

    return (
        <header className={styles.header}>
            <div className={styles.headerTitleWrap}>
                <span className={styles.headerTitle}>{title}</span>
            </div>
            <div className={styles.headerEnd}>
                <div className={styles.mobileTheme}>
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </div>
                {user && <AccountMenu key={user.id} />}
            </div>
        </header>
    );
}
