import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Button from '@shared/components/Button/Button';
import { useAdminClients } from '@features/administration/clients/hooks/useAdminClients';
import ClientsFilters from '@features/administration/clients/components/ClientsFilters';
import ClientsTable from '@features/administration/clients/components/ClientsTable';
import ClientsPagination from '@features/administration/clients/components/ClientsPagination';
import { ClientsListSkeleton } from '@features/administration/clients/components/ClientsSkeleton';
import styles from '@features/administration/clients/pages/AdminClients.module.css';

const PARAM_BY_FIELD = { search: 'search', status: 'status', planCode: 'plan_code', page: 'page' };

export default function AdministrationClientsPage() {
    const [params, setParams] = useSearchParams();

    const values = {
        search: params.get('search') ?? '',
        status: params.get('status') ?? '',
        planCode: params.get('plan_code') ?? '',
    };
    const page = Math.max(1, Number.parseInt(params.get('page') ?? '1', 10) || 1);
    const hasFilters = Boolean(values.search || values.status || values.planCode);

    const { data, loading, error, reload } = useAdminClients({ ...values, page });

    // Cambiar un filtro vuelve a la página 1; cambiar de página conserva los filtros.
    const updateParams = useCallback(
        (patch) => {
            setParams((prev) => {
                const next = new URLSearchParams(prev);
                Object.entries(patch).forEach(([field, value]) => {
                    const key = PARAM_BY_FIELD[field];
                    if (value) next.set(key, String(value));
                    else next.delete(key);
                });
                if (!('page' in patch)) next.delete('page');
                return next;
            });
        },
        [setParams],
    );

    const clearFilters = () => setParams(new URLSearchParams());
    const goToPage = (nextPage) => updateParams({ page: nextPage > 1 ? nextPage : '' });

    return (
        <section className={styles.page}>
            <header className={styles.heading}>
                <h1>Clientes</h1>
                <p>
                    Consulta el estado, el plan y el consumo de cada cliente. Por privacidad,
                    no se muestra el contenido de sus archivos.
                </p>
            </header>

            <ClientsFilters values={values} hasFilters={hasFilters} onApply={updateParams} onClear={clearFilters} />

            <div aria-busy={loading}>
                {loading && <ClientsListSkeleton />}

                {!loading && error && (
                    <div className={styles.alert} role="alert">
                        <p>{error}</p>
                        <Button type="button" variant="secondary" onClick={reload}>Reintentar</Button>
                    </div>
                )}

                {!loading && !error && data && data.results.length === 0 && (
                    <div className={`${styles.card} ${styles.empty}`}>
                        <h2>{hasFilters ? 'Ningún cliente coincide con los filtros' : 'Todavía no hay clientes'}</h2>
                        <p className={styles.muted}>
                            {hasFilters
                                ? 'Prueba con otro nombre o correo, o quita los filtros.'
                                : 'Cuando se registre un cliente, aparecerá aquí.'}
                        </p>
                        {hasFilters && (
                            <div className={styles.actions}>
                                <Button type="button" variant="secondary" onClick={clearFilters}>Limpiar filtros</Button>
                            </div>
                        )}
                    </div>
                )}

                {!loading && !error && data && data.results.length > 0 && (
                    <div className={styles.content}>
                        <p className={styles.muted} role="status">
                            {data.count} {data.count === 1 ? 'cliente' : 'clientes'}
                            {hasFilters ? ' con los filtros aplicados' : ''}
                        </p>
                        <ClientsTable clients={data.results} />
                        <ClientsPagination
                            page={page}
                            count={data.count}
                            hasPrev={Boolean(data.previous)}
                            hasNext={Boolean(data.next)}
                            onChange={goToPage}
                        />
                    </div>
                )}
            </div>
        </section>
    );
}