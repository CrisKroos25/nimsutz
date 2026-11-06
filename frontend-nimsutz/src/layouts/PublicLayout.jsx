import { useEffect, useId, useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Brand from './Brand';
import ThemeToggle from './ThemeToggle';
import styles from './PublicLayout.module.css';

// Enlace a una sección de la landing. Usa Link (sin recarga) y vuelve a "/" si estamos en otra ruta.
function SectionLink({ id, children, onNavigate }) {
    const { pathname } = useLocation();
    const to = pathname === '/' ? `#${id}` : `/#${id}`;
    return <Link to={to} onClick={onNavigate}>{children}</Link>;
}

export default function PublicLayout({ theme, toggleTheme }) {
    const [open, setOpen] = useState(false);
    const { pathname, hash, key } = useLocation();
    const menuId = useId();
    const close = () => setOpen(false);

    // Cierra el menú al cambiar de ruta.
    useEffect(() => { setOpen(false); }, [pathname]);

    // Cierra el menú con Escape.
    useEffect(() => {
        if (!open) return;
        const onKey = (event) => { if (event.key === 'Escape') setOpen(false); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open]);

    // En una SPA las anclas no hacen scroll solas. key cambia en cada clic, así también funciona al repetir el mismo ancla.
    useEffect(() => {
        if (!hash) return;
        const target = document.getElementById(decodeURIComponent(hash.slice(1)));
        target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, [key, pathname, hash]);

    return (
        <div className={styles.public}>
            <a href="#main-content" className={styles.skip}>Saltar al contenido</a>
            <header className={styles.publicHeader}>
                <div className={styles.headerContent}>
                    <Brand />
                    <nav aria-label="Navegación pública" className={styles.publicNav}>
                        <Link to="/login" className={styles.secondaryAction}>Iniciar sesión</Link>
                        <Link to="/register" className={styles.primaryAction}>Registro</Link>
                        <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                    </nav>
                    <button
                        type="button"
                        className={styles.menuButton}
                        aria-expanded={open}
                        aria-controls={menuId}
                        aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
                        onClick={() => setOpen((value) => !value)}
                    >
                        {open ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
                    </button>
                </div>
                <nav id={menuId} aria-label="Menú móvil" hidden={!open} className={styles.mobileMenu}>
                    <Link to="/login" onClick={close} >Iniciar sesión</Link>
                    <Link to="/register" onClick={close} >Registro</Link>
                    <SectionLink id="plans" onNavigate={close}>Planes</SectionLink>
                    <SectionLink id="about" onNavigate={close}>Sobre nosotros</SectionLink>
                    <div className={styles.mobileTheme}>
                        <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                    </div>
                </nav>
            </header>
            <main className={styles.main} id="main-content" tabIndex={-1}>
                <Outlet context={{ theme }} />
            </main>
            <footer className={styles.footer}>
                <div>
                    <Brand />
                    <p>Un lugar para tus documentos.<br />Más espacio para tus ideas.</p>
                </div>
                <nav aria-label="Navegación del pie">
                    <SectionLink id="about">Sobre nosotros</SectionLink>
                    <SectionLink id="features">Beneficios</SectionLink>
                    <SectionLink id="plans">Planes</SectionLink>
                    <SectionLink id="questions">Preguntas frecuentes</SectionLink>
                    <Link to="/login">Iniciar sesión</Link>
                </nav>
                <p>© {new Date().getFullYear()} Nim sutz’</p>
            </footer>
        </div>
    );
}