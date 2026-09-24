import { useState } from 'react';
import { Download, Trash2, MoreVertical } from 'lucide-react';
import styles from './FileActions.module.css';

export default function FileActions({ file, onChanged }) {
    const [isOpen, setIsOpen] = useState(false);

    // Función para manejar la descarga (Solicitud de URL firmada a Django/MinIO)
    const handleDownload = () => {
        console.log(`Solicitando descarga para el archivo: ${file.nombre}`);
        // Aquí conectaremos la llamada a la API para obtener la URL firmada
        setIsOpen(false);
    };

    // Función para enviar a papelera (Eliminación lógica)
    const handleSendToTrash = () => {
        console.log(`Enviando a papelera el archivo ID: ${file.id}`);
        // Aquí conectaremos el endpoint PATCH/DELETE lógico
        if (onChanged) onChanged(); // Notifica al explorador que hubo cambios
        setIsOpen(false);
    };

    return (
        <div className={styles.container}>
            <button 
                onClick={() => setIsOpen(!isOpen)} 
                className={styles.triggerBtn}
                aria-label="Acciones de archivo"
            >
                <MoreVertical size={18} />
            </button>

            {isOpen && (
                <div className={styles.dropdown}>
                    <button onClick={handleDownload} className={styles.menuItem}>
                        <Download size={16} />
                        <span>Descargar</span>
                    </button>
                    
                    <div className={styles.divider} />

                    <button onClick={handleSendToTrash} className={`${styles.menuItem} ${styles.danger}`}>
                        <Trash2 size={16} />
                        <span>Mover a papelera</span>
                    </button>
                </div>
            )}
        </div>
    );
}