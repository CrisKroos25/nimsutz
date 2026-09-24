import { useState } from 'react';
import { RotateCcw, Trash2, AlertCircle } from 'lucide-react';
import styles from './Trash.module.css';

export default function Trash() {
    // Estado con archivos de prueba en papelera (siguen consumiendo cuota)
    const [trashedFiles, setTrashedFiles] = useState([
        { id: 101, nombre: 'Banner_Campana_Sep.png', tamano: '4.2 MB', fecha: '10 sep 2026' },
        { id: 102, nombre: 'Contrato_Antiguo_v1.docx', tamano: '1.5 MB', fecha: '02 sep 2026' }
    ]);

    const [notification, setNotification] = useState(null);

    const showMessage = (msg) => {
        setNotification(msg);
        setTimeout(() => setNotification(null), 3000);
    };

    const handleRestore = (id, nombre) => {
        setTrashedFiles(trashedFiles.filter(f => f.id !== id));
        showMessage(`"${nombre}" ha sido restaurado a su ubicación original.`);
    };

    const handleDeletePermanent = (id, nombre) => {
        if (window.confirm(`¿Estás seguro de eliminar definitivamente "${nombre}"? Esta acción borrará el contenido físico de MinIO y liberará cuota de espacio.`)) {
            setTrashedFiles(trashedFiles.filter(f => f.id !== id));
            showMessage(`"${nombre}" eliminado de forma definitiva.`);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.headerArea}>
                <div>
                    <h2 className={styles.title}>Papelera de Reciclaje</h2>
                    <p className={styles.subtitle}>
                        Los elementos aquí ubicados continúan ocupando espacio en tu cuota de almacenamiento.
                    </p>
                </div>
            </div>

            {notification && (
                <div className={styles.notification}>
                    <AlertCircle size={18} />
                    <span>{notification}</span>
                </div>
            )}

            {trashedFiles.length === 0 ? (
                <div className={styles.emptyState}>
                    <Trash2 size={48} className={styles.emptyIcon} />
                    <h3>La papelera está vacía</h3>
                    <p>Los archivos que envíes a la papelera aparecerán aquí.</p>
                </div>
            ) : (
                <div className={styles.list}>
                    {trashedFiles.map(file => (
                        <div key={file.id} className={styles.item}>
                            <div>
                                <span className={styles.fileName}>{file.nombre}</span>
                                <span className={styles.fileMeta}>{file.tamano} • Eliminado el {file.fecha}</span>
                            </div>
                            <div className={styles.actions}>
                                <button 
                                    onClick={() => handleRestore(file.id, file.nombre)} 
                                    className={styles.restoreBtn}
                                    title="Restaurar archivo"
                                >
                                    <RotateCcw size={16} /> Restaurar
                                </button>
                                <button 
                                    onClick={() => handleDeletePermanent(file.id, file.nombre)} 
                                    className={styles.deleteBtn}
                                    title="Eliminar definitivamente"
                                >
                                    <Trash2 size={16} /> Eliminar definitivamente
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}