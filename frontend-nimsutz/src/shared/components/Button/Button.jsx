import styles from './Button.module.css';

export default function Button({
    children,
    variant = 'primary',
    type = 'button',
    disabled = false,
    loading = false,
    loadingLabel = 'Cargando…',
    className = '',
    ...props
}) {
    return (
        <button
            {...props}
            type={type}
            disabled={disabled || loading}
            aria-busy={loading || undefined}
            className={`${styles.button} ${styles[variant] || styles.primary} ${className}`}
        >
            {loading ? loadingLabel : children}
        </button>
    );
}
