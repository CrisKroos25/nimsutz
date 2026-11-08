import { useAuth } from '@shared/auth/AuthContext';
import { useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import AccountMenu from './AccountMenu';
import styles from './Layouts.module.css';

// Cada rama define su título y, si aplica, la ruta del perfil.
// Así el header no asume que todo lo que no es "/profile" es de cliente.
const CLIENT_TITLES = [
    ['/profile', 'Mi perfil'],
    ['/payments/checkout', 'Confirma tu plan'],
    ['/payments/result', 'Resultado del pago'],
    ['/payments/history', 'Historial de pagos'],
    ['/subscription', 'Mi suscripción'],
    ['/plans', 'Planes'],
    ['/trash', 'Papelera'],
    ['/files', 'Mis archivos'],
];

const ADMIN_TITLES = [
    ['/administration/clients', 'Clientes'],
    ['/administration/payments', 'Pagos'],
    ['/administration/plans', 'Catálogo de planes'],
    ['/administration/audit', 'Auditoría'],
    ['/administration', 'Panel'],
];

function titleFor(pathname, entries, fallback) {
    const match = entries.find(([prefix]) => pathname.startsWith(prefix));
    return match ? match[1] : fallback;
}

export default function Header({ theme, toggleTheme }) {
    const { user } = useAuth();
    const { pathname } = useLocation();
    const isAdmin = user?.role === 'administrador';

    const title = isAdmin
        ? titleFor(pathname, ADMIN_TITLES, 'Administración')
        : titleFor(pathname, CLIENT_TITLES, 'Mis archivos');

    return (
        <header className={styles.header}>
            <div className={styles.headerTitleWrap}>
                <span className={styles.headerTitle}>{title}</span>
            </div>
            <div className={styles.headerEnd}>
                <div className={styles.mobileTheme}>
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </div>
                {user && (
                    <AccountMenu
                        key={user.id}
                        profilePath={isAdmin ? null : '/profile'}
                    />
                )}
            </div>
        </header>
    );
}