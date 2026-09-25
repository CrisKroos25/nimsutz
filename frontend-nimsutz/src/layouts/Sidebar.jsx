import { Folder, Palette, Trash2 } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import Brand from './Brand';
import ThemeToggle from './ThemeToggle';
import styles from './Layouts.module.css';

const ITEMS = [
    { to: '/files', label: 'Mis archivos', icon: Folder },
    { to: '/trash', label: 'Papelera', icon: Trash2 },
    { to: '/design-system', label: 'Sistema de diseño', icon: Palette },
];

export default function Sidebar({ theme, toggleTheme }) {
    return (
        <aside className={styles.sidebar}>
            <Brand />
            <p className={styles.label}>MÓDULOS</p>
            <nav
                aria-label="Navegación de la aplicación"
                className={styles.navigation}
            >
                {ITEMS.map(({ to, label, icon: Icon }) => (
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
            <div className={styles.theme}>
                <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
            </div>
        </aside>
    );
}
