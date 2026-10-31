import { useEffect, useId, useRef } from 'react';
import styles from './Modal.module.css';

function keepTabInside(event) {
    if (event.key !== 'Tab') return;
    const dialog = event.currentTarget;
    const controls = [...dialog.querySelectorAll(
        'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )].filter((element) => !element.matches(':disabled, [inert], [type="hidden"]') && element.getClientRects().length);
    const first = controls[0];
    const last = controls.at(-1);
    if (!first) {
        event.preventDefault();
        dialog.focus();
    } else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

export default function Modal({
    open,
    onClose,
    title,
    description,
    icon,
    headerAction,
    className = '',
    children,
}) {
    const dialogRef = useRef(null);
    const titleId = useId();
    const descriptionId = useId();

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!open) return;
        const trigger = document.activeElement;
        const previousOverflow = document.body.style.overflow;
        dialog.showModal();
        document.body.style.overflow = 'hidden';
        return () => {
            dialog.close();
            document.body.style.overflow = previousOverflow;
            if (trigger instanceof HTMLElement && trigger.isConnected)
                trigger.focus();
        };
    }, [open]);

    return (
        <dialog
            ref={dialogRef}
            className={`${styles.dialog} ${icon ? styles.withIcon : ''} ${className}`}
            aria-labelledby={titleId}
            aria-describedby={description ? descriptionId : undefined}
            onKeyDown={keepTabInside}
            onCancel={(event) => {
                event.preventDefault();
                onClose();
            }}
        >
            <div className={styles.content}>
                <div className={`${styles.heading} ${headerAction ? styles.withAction : ''}`}>
                    {icon && (
                        <span className={styles.icon} aria-hidden="true">
                            {icon}
                        </span>
                    )}
                    <h2 id={titleId}>{title}</h2>
                    {headerAction}
                </div>
                {description && (
                    <p id={descriptionId} className={styles.description}>
                        {description}
                    </p>
                )}
                {children}
            </div>
        </dialog>
    );
}
