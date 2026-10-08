import { useId } from 'react';
import styles from './Input.module.css';

export default function Input({
    label,
    id,
    hint,
    error,
    leadingIcon,
    trailingAction,
    className = '',
    'aria-describedby': describedBy,
    ...props
}) {
    const generatedId = useId();
    const inputId = id || generatedId;
    const description =
        [describedBy, hint && `${inputId}-hint`, error && `${inputId}-error`]
            .filter(Boolean)
            .join(' ') || undefined;

    return (
        <div className={styles.field}>
            <label htmlFor={inputId} className={styles.label}>
                {label}
            </label>
            <div className={styles.control}>
                {leadingIcon && <span className={styles.leadingIcon} aria-hidden="true">{leadingIcon}</span>}
                <input
                    {...props}
                    id={inputId}
                    className={`${styles.input} ${leadingIcon ? styles.withIcon : ''} ${trailingAction ? styles.withAction : ''} ${className}`}
                    aria-invalid={error ? true : props['aria-invalid']}
                    aria-describedby={description}
                />
                {trailingAction && <span className={styles.trailingAction}>{trailingAction}</span>}
            </div>
            {hint && (
                <p id={`${inputId}-hint`} className={styles.hint}>
                    {hint}
                </p>
            )}
            {error && (
                <p
                    id={`${inputId}-error`}
                    className={styles.error}
                    role="alert"
                >
                    {error}
                </p>
            )}
        </div>
    );
}
