import { Folder, Receipt, Trash2, Wallet, ListTree, Layers} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useHasSubscription } from '@shared/hooks/useHasSubscription';
import Brand from './Brand';
import SidebarStorage from './SidebarStorage';
import ThemeToggle from './ThemeToggle';
import styles from './Layouts.module.css';

const FILES_ITEM = { to: '/files', label: 'Mis archivos', icon: Folder };
const PLANS_ITEM = { to: '/plans', label: 'Planes', icon: ListTree };

const CLIENT_ITEMS = [
    { to: '/files', label: 'Mis archivos', icon: Folder },
    { to: '/plans', label: 'Planes', icon: ListTree },
    { to: '/subscription', label: 'Mi suscripción', icon: Wallet },
    { to: '/payments/history', label: 'Pagos', icon: Receipt },
    { to: '/trash', label: 'Papelera', icon: Trash2 },
];

const ADMIN_ITEMS = [
    { to: '/administration/plans', label: 'Catálogo de planes', icon: Layers },
];

export default function Sidebar({ theme, toggleTheme }) {
    const hasSubscription = useHasSubscription();

    const navItems = [
    hasSubscription ? FILES_ITEM : PLANS_ITEM,
    ...CLIENT_ITEMS.filter((item) => item.to !== '/files' && item.to !== '/plans'),];

    return (
        <aside className={styles.sidebar}>
            <Brand />
            <p className={styles.label}>MÓDULOS</p>
            <nav
                aria-label="Navegación de la aplicación"
                className={styles.navigation}
            >
                {navItems.map(({ to, label, icon: Icon }) => (
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

            </nav>
            <div className={styles.footer}>
                <SidebarStorage />
                <div className={styles.theme}>
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </div>
            </div>
        </aside>
    );
}
