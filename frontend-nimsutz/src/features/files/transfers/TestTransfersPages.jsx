import { useState } from 'react';
import UploadPanel from './components/UploadPanel/UploadPanel';
import FileActions from './components/FileActions/FileActions';
import Trash from './components/TrashView/Trash';

export default function TestTransfersPages() {
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [files, setFiles] = useState([
        { id: 1, nombre: 'Informe_Anual_2025.pdf', tamano: '3.4 MB', estado: 'Disponible' },
        { id: 2, nombre: 'Presupuesto_Q3_2026.xlsx', tamano: '1.1 MB', estado: 'Procesando' }
    ]);

    return (
        <div style={{ padding: '2rem', background: '#0D0B1E', color: 'white', minHeight: '100vh' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1>Mis Archivos (Entorno de Pruebas - Integrante B)</h1>
                <button 
                    onClick={() => setShowUploadModal(true)}
                    style={{ background: '#f97316', border: 'none', color: 'white', padding: '0.75rem 1.5rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    + Subir archivo
                </button>
            </div>

            {/* Listado Provisional */}
            <div style={{ background: '#1a1638', borderRadius: '8px', overflow: 'hidden', border: '1px solid #332d66', marginBottom: '3rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                        <tr style={{ background: '#25214d', borderBottom: '1px solid #332d66' }}>
                            <th style={{ padding: '1rem' }}>Nombre</th>
                            <th style={{ padding: '1rem' }}>Tamaño</th>
                            <th style={{ padding: '1rem' }}>Estado</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {files.map(file => (
                            <tr key={file.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <td style={{ padding: '1rem' }}>{file.nombre}</td>
                                <td style={{ padding: '1rem', color: '#94a3b8' }}>{file.tamano}</td>
                                <td style={{ padding: '1rem' }}>
                                    <span style={{ color: file.estado === 'Disponible' ? '#4ade80' : '#fbbf24' }}>
                                        ● {file.estado}
                                    </span>
                                </td>
                                <td style={{ padding: '1rem', textAlign: 'right' }}>
                                    <FileActions file={file} onChanged={() => setFiles(files.filter(f => f.id !== file.id))} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Sección de Papelera que pediste */}
            <div style={{ borderTop: '1px solid #332d66', paddingTop: '2rem' }}>
                <Trash />
            </div>

            {showUploadModal && (
                <UploadPanel 
                    folderId={null} 
                    onCompleted={() => setShowUploadModal(false)} 
                    onClose={() => setShowUploadModal(false)} 
                />
            )}
        </div>
    );
}