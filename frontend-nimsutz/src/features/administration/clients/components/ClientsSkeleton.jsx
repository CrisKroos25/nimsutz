import styles from '../pages/AdminClients.module.css';

export function ClientsListSkeleton() {
    return (
        <div className={`${styles.skeleton} ${styles.pulse}`} aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
                <article key={i} className={`${styles.card} ${styles.skeletonRow}`}>
                    <div className={`${styles.skeletonLine} ${styles.wide}`} />
                    <div className={`${styles.skeletonLine} ${styles.short}`} />
                </article>
            ))}
        </div>
    );
}

export function ClientDetailSkeleton() {
    return (
        <div className={`${styles.skeleton} ${styles.pulse}`} aria-hidden="true">
            <div className={styles.grid}>
                <article className={`${styles.card} ${styles.skeletonCard}`}>
                    <div className={`${styles.skeletonLine} ${styles.wide}`} />
                    <div className={styles.skeletonLine} />
                    <div className={styles.skeletonLine} />
                    <div className={styles.skeletonLine} />
                </article>
                <article className={`${styles.card} ${styles.skeletonCard}`}>
                    <div className={`${styles.skeletonLine} ${styles.wide}`} />
                    <div className={styles.skeletonLine} />
                    <div className={`${styles.skeletonLine} ${styles.short}`} />
                </article>
            </div>
            <article className={`${styles.card} ${styles.skeletonRow}`}>
                <div className={`${styles.skeletonLine} ${styles.wide}`} />
                <div className={styles.skeletonLine} />
            </article>
        </div>
    );
}