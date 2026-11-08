import Button from '@shared/components/Button/Button';
import styles from '../pages/AdminClients.module.css';

export default function ClientsPagination({ page, count, pageSize = 20, hasPrev, hasNext, onChange }) {
    const totalPages = Math.max(1, Math.ceil(count / pageSize));
    if (totalPages <= 1) return null;
    return (
        <nav className={styles.pager} aria-label="Paginación de clientes">
            <Button type="button" variant="secondary" onClick={() => onChange(page - 1)} disabled={!hasPrev}>
                Anterior
            </Button>
            <span className={styles.muted}>Página {page} de {totalPages}</span>
            <Button type="button" variant="secondary" onClick={() => onChange(page + 1)} disabled={!hasNext}>
                Siguiente
            </Button>
        </nav>
    );
}