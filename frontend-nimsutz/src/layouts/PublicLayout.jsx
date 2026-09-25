import { Outlet, Link } from 'react-router-dom';
import Brand from './Brand';
import ThemeToggle from './ThemeToggle';
import styles from './PublicLayout.module.css';

export default function PublicLayout({ theme, toggleTheme }) {
    return (
        <div className={styles.public}>
            <a href="#main-content" className={styles.skip}>Saltar al contenido</a>
            <header className={styles.publicHeader}>
                <div className={styles.headerContent}>
                <Brand />
                <nav aria-label="Navegación pública" className={styles.publicNav}>
                    <a href="/#plans">Planes</a>
                    <Link to="/login">Iniciar sesión</Link>
                    <span role="link" aria-disabled="true" className={styles.register}>Registro</span>
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </nav>
                </div>
            </header>
            <main className={styles.main} id="main-content" tabIndex={-1}><Outlet /></main>
            <footer className={styles.footer}>
                <div><Brand /><p>Un lugar para tus documentos.<br />Más espacio para tus ideas.</p></div>
                <nav aria-label="Navegación del pie">
                    <Link to="/about">Sobre nosotros</Link>
                    <a href="/#features">Beneficios</a>
                    <a href="/#plans">Planes</a>
                    <a href="/#questions">Preguntas frecuentes</a>
                    <Link to="/login">Iniciar sesión</Link>
                </nav>
                <p>© {new Date().getFullYear()} Nim sutz’</p>
            </footer>
        </div>
    );
}
