import styles from './Badge.module.css';

export default function Badge({ children, tone = 'neutral' }) {
    const tones = ['success', 'danger', 'warning', 'info', 'neutral'];
    return (
        <span
            className={`${styles.badge} ${styles[tones.includes(tone) ? tone : 'neutral']}`}
        >
            <span className={styles.dot} aria-hidden="true" />
            {children}
        </span>
    );
}
