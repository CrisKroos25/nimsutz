import { useEffect, useState } from 'react';
import Button from '@shared/components/Button/Button';
import { STATUS_OPTIONS } from '../utils/clientStatus';
import styles from '../pages/AdminClients.module.css';

/**
 * Búsqueda y plan se aplican al enviar el formulario (Enter o "Buscar");
 * el estado se aplica al elegirlo. Los valores reales viven en la URL.
 */
export default function ClientsFilters({ values, hasFilters, onApply, onClear }) {
    const [search, setSearch] = useState(values.search);
    const [planCode, setPlanCode] = useState(values.planCode);

    useEffect(() => setSearch(values.search), [values.search]);
    useEffect(() => setPlanCode(values.planCode), [values.planCode]);

    const handleSubmit = (event) => {
        event.preventDefault();
        onApply({ search: search.trim(), planCode: planCode.trim() });
    };

    return (
        <form className={styles.filters} role="search" aria-label="Filtrar clientes" onSubmit={handleSubmit}>
            <div className={styles.field}>
                <label htmlFor="client-search">Nombre o correo</label>
                <input
                    id="client-search"
                    type="search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Ej. Carlos o correo@dominio.com"
                    autoComplete="off"
                />
            </div>
            <div className={styles.field}>
                <label htmlFor="client-status">Estado</label>
                <select id="client-status" value={values.status} onChange={(e) => onApply({ status: e.target.value })}>
                    <option value="">Todos</option>
                    {STATUS_OPTIONS.map(({ value, label }) => (
                        <option key={value} value={value}>{label}</option>
                    ))}
                </select>
            </div>
            <div className={styles.field}>
                <label htmlFor="client-plan">Código de plan</label>
                <input
                    id="client-plan"
                    type="text"
                    value={planCode}
                    onChange={(e) => setPlanCode(e.target.value)}
                    autoComplete="off"
                />
            </div>
            <div className={`${styles.actions} ${styles.filterActions}`}>
                <Button type="submit">Buscar</Button>
                {hasFilters && (
                    <Button type="button" variant="secondary" onClick={onClear}>
                        Limpiar filtros
                    </Button>
                )}
            </div>
        </form>
    );
}