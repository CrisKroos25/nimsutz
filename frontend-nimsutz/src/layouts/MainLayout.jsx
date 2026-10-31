import { useEffect, useRef } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import styles from './Layouts.module.css';

export default function MainLayout({ theme, toggleTheme }) {
    const content = useRef(null);
    const { pathname } = useLocation();
    useEffect(() => {
        // Al navegar, el teclado continúa en la pantalla nueva, sin robar foco a un modal.
        if (!document.querySelector('dialog[open]')) content.current?.focus({ preventScroll: true });
        window.scrollTo(0, 0);
    }, [pathname]);
    return (
        <div className={styles.app}>
            <a href="#main-content" className={styles.skip}>
                Saltar al contenido
            </a>
            <Sidebar theme={theme} toggleTheme={toggleTheme} />
            <div className={styles.workspace}>
                <Header theme={theme} toggleTheme={toggleTheme} />
                <main ref={content} tabIndex={-1} id="main-content" className={styles.content}>
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
