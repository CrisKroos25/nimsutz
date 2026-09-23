import { useState } from 'react';
import Badge from '@shared/components/Badge/Badge';
import Table from '@shared/components/Table/Table';
import Button from '@shared/components/Button/Button';
import styles from '../DesignSystemPage.module.css';

const STATES = [
    ['success', 'Completado'],
    ['danger', 'Cuota agotada'],
    ['warning', 'Pendiente'],
    ['info', 'En proceso'],
    ['neutral', 'Borrador'],
];
const ROWS = [
    {
        id: 1,
        name: 'Informe_Anual_2024.pdf',
        type: 'PDF',
        size: '3.4 MB',
        date: '08 sep 2026',
        owner: 'Gimena Ruiz',
        tone: 'success',
        status: 'Completado',
    },
    {
        id: 2,
        name: 'Presupuesto_Q3.xlsx',
        type: 'Excel',
        size: '1.1 MB',
        date: '05 sep 2026',
        owner: 'Carlos M.',
        tone: 'info',
        status: 'En proceso',
    },
    {
        id: 3,
        name: 'Contrato_Proveedor.docx',
        type: 'Word',
        size: '542 KB',
        date: '01 sep 2026',
        owner: 'Ana Torres',
        tone: 'warning',
        status: 'Pendiente',
    },
];
const COLUMNS = [
    { key: 'name', label: 'Nombre' },
    { key: 'type', label: 'Tipo' },
    { key: 'size', label: 'Tamaño' },
    { key: 'date', label: 'Fecha' },
    { key: 'owner', label: 'Propietario' },
    {
        key: 'status',
        label: 'Estado',
        render: (row) => <Badge tone={row.tone}>{row.status}</Badge>,
    },
];

export default function TableExamples() {
    const [state, setState] = useState('data');
    return (
        <>
            <section aria-labelledby="badges-title">
                <h2 id="badges-title" className={styles.sectionTitle}>
                    Insignias de estado
                </h2>
                <div className={styles.panel}>
                    <div className={styles.row}>
                        {STATES.map(([tone, label]) => (
                            <Badge key={tone} tone={tone}>
                                {label}
                            </Badge>
                        ))}
                    </div>
                </div>
            </section>
            <section aria-labelledby="table-title">
                <h2 id="table-title" className={styles.sectionTitle}>
                    Tabla de archivos
                </h2>
                <div className={styles.panel}>
                    <div className={styles.row}>
                        {[
                            ['data', 'Con datos'],
                            ['empty', 'Vacía'],
                            ['loading', 'Cargando'],
                            ['error', 'Con error'],
                        ].map(([value, label]) => (
                            <Button
                                key={value}
                                variant="secondary"
                                aria-pressed={state === value}
                                onClick={() => setState(value)}
                            >
                                {label}
                            </Button>
                        ))}
                    </div>
                    <Table
                        caption="Archivos de ejemplo del design system"
                        columns={COLUMNS}
                        rows={state === 'empty' ? [] : ROWS}
                        loading={state === 'loading'}
                        error={
                            state === 'error'
                                ? 'No se pudieron cargar los archivos. Intenta nuevamente.'
                                : undefined
                        }
                    />
                </div>
            </section>
        </>
    );
}
