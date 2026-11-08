// Sidebar.jsx
import { NavLink } from 'react-router-dom';
import Brand from './Brand';
import ThemeToggle from './ThemeToggle';
import styles from './Layouts.module.css';

export default function Sidebar({ theme, toggleTheme, items, footer = null }) {
    return (
        <aside className={styles.sidebar}>
            <Brand />
            <p className={styles.label}>MÓDULOS</p>
            <nav aria-label="Navegación de la aplicación" className={styles.navigation}>
                {items.map(({ to, label, icon: Icon, end }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={end}
                        className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}
                    >
                        <Icon size={18} aria-hidden="true" />
                        {label}
                    </NavLink>
                ))}
            </nav>
            <div className={styles.footer}>
                {footer}
                <div className={styles.theme}>
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </div>
            </div>
        </aside>
    );
}