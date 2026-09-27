import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import styles from './Layouts.module.css';

export default function MainLayout({ theme, toggleTheme }) {
    return (
        <div className={styles.app}>
            <a href="#main-content" className={styles.skip}>
                Saltar al contenido
            </a>
            <Sidebar theme={theme} toggleTheme={toggleTheme} />
            <div className={styles.workspace}>
                <Header />
                <main id="main-content" className={styles.content}>
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
