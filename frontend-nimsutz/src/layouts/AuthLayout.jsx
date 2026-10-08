import { useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import styles from './AuthLayout.module.css';

export default function AuthLayout({ theme, toggleTheme }) {
    const { pathname } = useLocation();
    useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
    return (
        <main className={styles.shell} id="main-content">
            <div className={styles.card}>
                <div className={styles.toolbar}>
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </div>
                <Outlet />
            </div>
            <Link to="/" className={styles.back}>Volver al inicio</Link>
        </main>
    );
}
