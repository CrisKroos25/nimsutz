import { Folder, Receipt, Trash2, Wallet, Layers } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '@shared/auth/AuthContext';
import Brand from './Brand';
import ThemeToggle from './ThemeToggle';
import styles from './Layouts.module.css';

const CLIENT_ITEMS = [
    { to: '/files', label: 'Mis archivos', icon: Folder },
    { to: '/trash', label: 'Papelera', icon: Trash2 },
    { to: '/subscription', label: 'Suscripción', icon: Wallet },
    { to: '/payments/history', label: 'Pagos', icon: Receipt },
];

const ADMIN_ITEMS = [
    { to: '/administration/plans', label: 'Catálogo de planes', icon: Layers },
];

export default function Sidebar({ theme, toggleTheme }) {
    const { user } = useAuth();
    const isAdmin = user?.role === 'administrador';

    return (
        <aside className={styles.sidebar}>
            <Brand />
            <p className={styles.label}>MÓDULOS</p>
            <nav
                aria-label="Navegación de la aplicación"
                className={styles.navigation}
            >
                {CLIENT_ITEMS.map(({ to, label, icon: Icon }) => (
                    <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                            `${styles.navLink} ${isActive ? styles.active : ''}`
                        }
                    >
                        <Icon size={18} aria-hidden="true" />
                        {label}
                    </NavLink>
                ))}

                {isAdmin && (
                    <>
                        <p className={styles.label} style={{ marginTop: '16px' }}>ADMINISTRACIÓN</p>
                        {ADMIN_ITEMS.map(({ to, label, icon: Icon }) => (
                            <NavLink
                                key={to}
                                to={to}
                                className={({ isActive }) =>
                                    `${styles.navLink} ${isActive ? styles.active : ''}`
                                }
                            >
                                <Icon size={18} aria-hidden="true" />
                                {label}
                            </NavLink>
                        ))}
                    </>
                )}
            </nav>
            <div className={styles.theme}>
                <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
            </div>
        </aside>
    );
}
