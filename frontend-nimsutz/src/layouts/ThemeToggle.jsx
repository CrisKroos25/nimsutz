import { Moon, Sun } from 'lucide-react';
import Button from '@shared/components/Button/Button';

export default function ThemeToggle({ theme, toggleTheme }) {
    const Icon = theme === 'light' ? Moon : Sun;
    return (
        <Button variant="ghost" onClick={toggleTheme}>
            <Icon size={18} aria-hidden="true" />
            {theme === 'light' ? 'Modo oscuro' : 'Modo claro'}
        </Button>
    );
}
