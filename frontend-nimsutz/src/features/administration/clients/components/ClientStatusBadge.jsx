import { getStatusMeta } from '../utils/clientStatus';
import styles from '../pages/AdminClients.module.css';


/** El estado se comunica con texto, no solo con color. */
export default function ClientStatusBadge({ status }) {
    const { label, tone } = getStatusMeta(status);
    return <span className={`${styles.badge} ${styles[`badge_${tone}`]}`}>{label}</span>;
}