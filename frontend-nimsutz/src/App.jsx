import DesignSystemPage from './pages/DesignSystemPage';
import Button from './shared/components/Button/Button';
import useTheme from './shared/hooks/useTheme';
import styles from './pages/DesignSystemPage.module.css';

export default function App() {
    const { theme, toggleTheme } = useTheme();
    return (
        <>
            <header className={`${styles.page} ${styles.header}`}>
                <strong>Nim sutz’</strong>
                <Button variant="secondary" onClick={toggleTheme}>
                    {theme === 'light' ? 'Activar tema oscuro' : 'Activar tema claro'}
                </Button>
            </header>
            <main><DesignSystemPage /></main>
        </>
    );
}
