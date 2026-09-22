import { useEffect, useId, useRef } from 'react';
import styles from './Modal.module.css';

export default function Modal({
    open,
    onClose,
    title,
    description,
    icon,
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
            className={`${styles.dialog} ${icon ? styles.withIcon : ''}`}
            aria-labelledby={titleId}
            aria-describedby={description ? descriptionId : undefined}
            onCancel={(event) => {
                event.preventDefault();
                onClose();
            }}
        >
            <div className={styles.content}>
                <div className={styles.heading}>
                    {icon && (
                        <span className={styles.icon} aria-hidden="true">
                            {icon}
                        </span>
                    )}
                    <h2 id={titleId}>{title}</h2>
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
