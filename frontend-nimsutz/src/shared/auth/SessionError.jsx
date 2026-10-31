import { AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../components/Button/Button';
import styles from './SessionLoader.module.css';

// Estado de error con el mismo diseño que SessionLoader.
export default function SessionError({
    message,
    onRetry,
    fullScreen = false,
    title = 'No pudimos comprobar tu sesión',
}) {
    return (
        <div
            className={`${styles.wrapper} ${fullScreen ? styles.fullScreen : ''}`}
            role="alert"
        >
            <span className={styles.icon} aria-hidden="true">
                <AlertTriangle size={36} />
            </span>
            <p className={styles.message}>{title}</p>
            {message && <p className={styles.hint}>{message}</p>}
            <div className={styles.actions}>
                {onRetry && <Button onClick={onRetry}>Reintentar</Button>}
                <Link to="/" className={styles.homeLink}>Volver al inicio</Link>
            </div>
        </div>
    );
}