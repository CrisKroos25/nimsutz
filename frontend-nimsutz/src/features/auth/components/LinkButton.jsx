import { Link } from 'react-router-dom';
import buttonStyles from '@shared/components/Button/Button.module.css';
import styles from '../pages/Recovery.module.css';

// Navegación con la apariencia del Button del design system (un enlace, no un botón).
export default function LinkButton({ to, variant = 'primary', children }) {
    return (
        <Link to={to} className={`${buttonStyles.button} ${buttonStyles[variant]} ${styles.linkButton}`}>
            {children}
        </Link>
    );
}
