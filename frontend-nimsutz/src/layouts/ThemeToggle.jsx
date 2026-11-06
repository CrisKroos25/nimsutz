import { Moon, Sun } from 'lucide-react';
import Button from '@shared/components/Button/Button';
import styles from './ThemeToggle.module.css';

export default function ThemeToggle({ theme, toggleTheme }) {
    const Icon = theme === 'light' ? Moon : Sun;
    const label = theme === 'light' ? 'Modo oscuro' : 'Modo claro';
    return (
        <Button variant="ghost" onClick={toggleTheme} aria-label={label} className={styles.toggle}>
            <Icon size={18} aria-hidden="true" />
            <span className={styles.text}>{label}</span>
        </Button>
    );
}