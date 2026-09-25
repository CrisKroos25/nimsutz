import { Link } from 'react-router-dom';
import { FolderOpen } from 'lucide-react';
import styles from './DesignSystemPage.module.css';

export default function StoragePreviewPage() {
    return (
        <section className={styles.main} aria-labelledby="files-title">
            <h1 id="files-title">Mis archivos</h1>
            <div className={styles.panel}>
                <FolderOpen size={32} aria-hidden="true" />
                <h2>El espacio para tus archivos está preparado</h2>
                <p>
                    Esta vista contiene el marco visual. La carga, descarga y
                    organización se conectarán al módulo de almacenamiento del
                    equipo.
                </p>
                <p className={styles.muted}>
                    Todavía no se consultan ni se modifican archivos en esta
                    rama.
                </p>
                <Link to="/design-system">Ver los componentes disponibles</Link>
            </div>
        </section>
    );
}
