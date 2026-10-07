import { Link } from 'react-router-dom';
import logo from '../assets/nimsutz-logo.png';
import styles from './Brand.module.css';

export default function Brand({ showName = true, className = '' }) {
    return (
        <Link to="/" className={`${styles.brand} ${className}`} aria-label="Nim sutz’, inicio">
            <img src={logo} className={styles.logo} alt="" width="44" height="44" />
            {showName && <strong>Nim sutz’</strong>}
        </Link>
    );
}
