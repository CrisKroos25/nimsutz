import { useEffect, useState } from 'react';

const STORAGE_KEY = 'nimsutz-theme';

function getInitialTheme() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === 'light' || saved === 'dark') return saved;
    } catch {
        // El tema funciona aunque el navegador bloquee el almacenamiento.
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
}

export default function useTheme() {
    const [theme, setTheme] = useState(getInitialTheme);

    useEffect(() => {
        document.documentElement.dataset.theme = theme;
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch {
            // Guardar la preferencia es opcional; aplicar el tema no lo es.
        }
    }, [theme]);

    function toggleTheme() {
        setTheme((current) => (current === 'light' ? 'dark' : 'light'));
    }

    return { theme, toggleTheme };
}
