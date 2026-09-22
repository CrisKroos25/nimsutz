import { useId } from 'react';
import styles from './Table.module.css';

export default function Table({
    columns,
    rows,
    rowKey = 'id',
    caption,
    loading = false,
    error,
    emptyMessage = 'No hay elementos para mostrar.',
}) {
    const captionId = useId();
    const message = loading
        ? 'Cargando…'
        : error || (rows.length === 0 ? emptyMessage : null);
    return (
        <div
            className={styles.scroll}
            role="region"
            aria-labelledby={captionId}
            tabIndex={0}
        >
            <table className={styles.table} aria-busy={loading}>
                <caption id={captionId}>{caption}</caption>
                <thead>
                    <tr>
                        {columns.map((column) => (
                            <th key={column.key} scope="col">
                                {column.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {message ? (
                        <tr>
                            <td
                                colSpan={columns.length}
                                className={styles.message}
                            >
                                <span
                                    role={
                                        error && !loading ? 'alert' : 'status'
                                    }
                                >
                                    {message}
                                </span>
                            </td>
                        </tr>
                    ) : (
                        rows.map((row) => (
                            <tr
                                key={
                                    typeof rowKey === 'function'
                                        ? rowKey(row)
                                        : row[rowKey]
                                }
                            >
                                {columns.map((column) => (
                                    <td key={column.key}>
                                        {column.render
                                            ? column.render(row)
                                            : row[column.key]}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
}
