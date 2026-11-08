import { Link } from 'react-router-dom';
import { formatStorage, formatDate } from '@shared/utils/planFormat';
import ClientStatusBadge from './ClientStatusBadge';
import styles from '../pages/AdminClients.module.css';

/**
 * Tabla en escritorio; en móvil el CSS la convierte en tarjetas (data-label).
 * Los roles explícitos mantienen la semántica de tabla al cambiar el `display`.
 */
export default function ClientsTable({ clients }) {
    return (
        <div className={styles.tableWrap}>
            <table className={styles.table} role="table">
                <caption className={styles.srOnly}>Lista de clientes</caption>
                <thead role="rowgroup">
                    <tr role="row">
                        <th scope="col" role="columnheader">Cliente</th>
                        <th scope="col" role="columnheader">Estado</th>
                        <th scope="col" role="columnheader">Plan</th>
                        <th scope="col" role="columnheader">Vigencia</th>
                        <th scope="col" role="columnheader">Consumo</th>
                        <th scope="col" role="columnheader">Archivos</th>
                        <th scope="col" role="columnheader"><span className={styles.srOnly}>Acciones</span></th>
                    </tr>
                </thead>
                <tbody role="rowgroup">
                    {clients.map((client) => (
                        <tr key={client.id} role="row">
                            <td role="cell" className={styles.identity}>
                                <strong>{client.name}</strong>
                                <span className={styles.muted}>{client.email}</span>
                            </td>
                            <td role="cell" data-label="Estado" className={styles.statusCell}><ClientStatusBadge status={client.account_status} /></td>
                            <td role="cell" data-label="Plan">{client.plan?.name ?? 'Sin plan'}</td>
                            <td role="cell" data-label="Vigencia">{client.coverage_end ? formatDate(client.coverage_end) : '—'}</td>
                            <td role="cell" data-label="Consumo">{formatStorage(client.usage_bytes)}</td>
                            <td role="cell" data-label="Archivos">{client.file_count}</td>
                            <td role="cell" className={styles.rowAction}>
                                <Link
                                    to={`/administration/clients/${client.id}`}
                                    className={styles.secondaryLink}
                                    aria-label={`Ver detalle de ${client.name}`}
                                >
                                    Ver detalle
                                </Link>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}