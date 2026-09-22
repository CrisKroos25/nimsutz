import { useLocation } from 'react-router-dom';
import styles from './Layouts.module.css';

export default function Header() {
    const { pathname } = useLocation();
    return (
        <header className={styles.header}>
            <span>
                {pathname === '/design-system'
                    ? 'Sistema de diseño'
                    : 'Mis archivos'}
            </span>
            <span className={styles.label}>Sprint 1</span>
        </header>
    );
}
