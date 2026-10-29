import { useEffect, useState } from 'react';
import styles from './SessionLoader.module.css';

// Espera con spinner. No se muestra de inmediato para evitar el parpadeo en cargas rápidas.
export default function SessionLoader({
    message = 'Comprobando tu sesión…',
    fullScreen = false,
    delay = 250,
    slowAfter = 6000,
}) {
    const [phase, setPhase] = useState('hidden'); // hidden → visible → slow

    useEffect(() => {
        const show = setTimeout(() => setPhase('visible'), delay);
        const slow = setTimeout(() => setPhase('slow'), slowAfter);
        return () => { clearTimeout(show); clearTimeout(slow); };
    }, [delay, slowAfter]);

    if (phase === 'hidden') return null;

    return (
        <div
            className={`${styles.wrapper} ${fullScreen ? styles.fullScreen : ''}`}
            role="status"
            aria-live="polite"
        >
            <span className={styles.spinner} aria-hidden="true" />
            <p className={styles.message}>{message}</p>
            {phase === 'slow' && (
                <p className={styles.hint}>
                    Esto está tardando más de lo normal. Revisa tu conexión; seguimos intentándolo.
                </p>
            )}
        </div>
    );
}