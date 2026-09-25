/* 	Pantallas completas que conecta el router.

   Esta página es SOLO el explorador de A: navegación de carpetas,
   crear/renombrar/eliminar carpeta, y el listado de archivos en modo
   lectura. La papelera (/trash) es una página autónoma de B y no vive
   aquí — ver src/router/AppRouter.jsx.

   Puntos de integración con B (contrato mínimo A-B):
     - Donde dice <UploadPanelPlaceholder />, cuando Rodrigo entregue
       UploadPanel, se reemplaza por:
         <UploadPanel folderId={folderId} onCompleted={reload} />
     - Donde dice <FileActionsPlaceholder />, cuando Rodrigo entregue
       FileActions, se reemplaza por:
         <FileActions file={row} onChanged={reload} /> */
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    Folder as FolderIcon,
    File as FileIcon,
    FolderPlus,
    Pencil,
    Trash2,
} from 'lucide-react';
import Table from '@shared/components/Table/Table';
import Button from '@shared/components/Button/Button';
import Badge from '@shared/components/Badge/Badge';
import { useFiles } from '../hooks/useFiles';
import FolderFormModal from '../components/FolderFormModal';
import ConfirmDialog from '../components/ConfirmDialog';
import styles from './FilePages.module.css';

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(
        Math.floor(Math.log(bytes) / Math.log(1024)),
        units.length - 1,
    );
    const value = bytes / 1024 ** exponent;
    return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function formatDate(isoString) {
    return new Date(isoString).toLocaleDateString('es-GT', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    });
}

/**
 * Reconstruye la ruta Raíz -> ... -> carpeta actual caminando hacia
 * arriba por el campo "parent" de cada carpeta, usando el índice
 * completo que trae useFiles. Esto es lo que reemplaza al breadcrumb
 * armado a mano con clics: siempre refleja la carpeta real, sin
 * importar si llegaste ahí con clics, con el botón "atrás" del
 * navegador, con un link directo, o recargando la página.
 */
function buildBreadcrumb(folderIndex, folderId) {
    const path = [];
    let currentId = folderId;
    while (currentId != null) {
        const folder = folderIndex.get(currentId);
        if (!folder) break;
        path.unshift({ id: folder.id, name: folder.name });
        currentId = folder.parent;
    }
    return path;
}

/** Reemplazar por <UploadPanel folderId={folderId} onCompleted={reload} /> cuando B lo entregue. */
function UploadPanelPlaceholder() {
    return (
        <Badge tone="warning">
            Subir archivo: pendiente de Rodrigo (UploadPanel)
        </Badge>
    );
}

/** Reemplazar por <FileActions file={row} onChanged={reload} /> cuando B lo entregue. */
function FileActionsPlaceholder() {
    return (
        <span className={styles.pending}>Acciones pendientes (Rodrigo)</span>
    );
}

/**
 * Explorador de archivos: navega carpetas dentro de "?folder=<id>" y
 * muestra las subcarpetas + archivos de la carpeta actual. El folderId
 * queda en la URL a propósito: así la carpeta actual persiste si se
 * recarga la página, tal como pide la consigna. El breadcrumb ahora se
 * deriva de datos del servidor (ver buildBreadcrumb), así que también
 * sobrevive a recargar la página o usar el botón "atrás".
 */
export function FilesPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const folderIdParam = searchParams.get('folder');
    const folderId = folderIdParam ? Number(folderIdParam) : null;

    const {
        folders,
        files,
        folderIndex,
        loading,
        error,
        reload,
        createFolder,
        renameFolder,
        deleteFolder,
    } = useFiles(folderId);

    const breadcrumb = buildBreadcrumb(folderIndex, folderId);

    const [createOpen, setCreateOpen] = useState(false);
    const [renameTarget, setRenameTarget] = useState(null);
    const [deleteTarget, setDeleteTarget] = useState(null);

    function openFolder(folder) {
        setSearchParams({ folder: String(folder.id) });
    }

    function goToRoot() {
        setSearchParams({});
    }

    function goToBreadcrumbIndex(index) {
        setSearchParams({ folder: String(breadcrumb[index].id) });
    }

    const columns = [
        {
            key: 'name',
            label: 'Nombre',
            render: (row) =>
                row.__type === 'folder' ? (
                    <button
                        type="button"
                        className={styles.name}
                        onClick={() => openFolder(row)}
                    >
                        <FolderIcon size={20} aria-hidden="true" /> {row.name}
                    </button>
                ) : (
                    <span className={styles.name}>
                        <FileIcon size={20} aria-hidden="true" />{' '}
                        {row.original_name}
                    </span>
                ),
        },
        {
            key: 'type',
            label: 'Tipo',
            render: (row) =>
                row.__type === 'folder' ? 'Carpeta' : row.content_type,
        },
        {
            key: 'size',
            label: 'Tamaño',
            render: (row) =>
                row.__type === 'folder' ? '-' : formatBytes(row.size_bytes),
        },
        {
            key: 'updated_at',
            label: 'Fecha',
            render: (row) => formatDate(row.updated_at),
        },
        {
            key: 'actions',
            label: 'Acciones',
            render: (row) =>
                row.__type === 'folder' ? (
                    <div className={styles.rowActions}>
                        <button
                            type="button"
                            className={styles.linkAction}
                            onClick={() => setRenameTarget(row)}
                        >
                            <Pencil size={18} />
                        </button>
                        <button
                            type="button"
                            className={styles.dangerAction}
                            onClick={() => setDeleteTarget(row)}
                        >
                            <Trash2 size={18} />
                        </button>
                    </div>
                ) : (
                    <FileActionsPlaceholder />
                ),
        },
    ];

    const rows = [
        ...folders.map((folder) => ({ ...folder, __type: 'folder' })),
        ...files.map((file) => ({ ...file, __type: 'file' })),
    ];

    return (
        <section className={styles.page} aria-labelledby="files-title">
            <h1 id="files-title" className={styles.srOnly}>
                Mis archivos
            </h1>

            <nav aria-label="Ruta de carpetas" className={styles.breadcrumb}>
                <button
                    type="button"
                    className={styles.breadcrumbButton}
                    onClick={goToRoot}
                >
                    Raíz
                </button>
                {breadcrumb.map((crumb, index) => (
                    <span key={crumb.id}>
                        {' / '}
                        <button
                            type="button"
                            className={styles.breadcrumbButton}
                            onClick={() => goToBreadcrumbIndex(index)}
                        >
                            {crumb.name}
                        </button>
                    </span>
                ))}
            </nav>

            <div className={styles.toolbar}>
                <div className={styles.actions}>
                    <Button type="button" onClick={() => setCreateOpen(true)}>
                        <FolderPlus size={16} aria-hidden="true" /> Nueva
                        carpeta
                    </Button>
                    {folderId != null && <UploadPanelPlaceholder />}
                </div>
                {folderId == null && (
                    <Badge tone="info">
                        Entra a una carpeta para subir archivos
                    </Badge>
                )}
            </div>

            {error && (
                <p className={styles.banner} role="alert">
                    {error}
                </p>
            )}

            <Table
                caption={
                    folderId == null
                        ? 'Carpetas en la raíz'
                        : 'Contenido de la carpeta'
                }
                columns={columns}
                rows={rows}
                rowKey={(row) => `${row.__type}-${row.id}`}
                loading={loading}
                emptyMessage="Esta carpeta está vacía."
            />

            <FolderFormModal
                open={createOpen}
                onClose={() => setCreateOpen(false)}
                onSubmit={(name) => createFolder(name)}
            />
            <FolderFormModal
                open={Boolean(renameTarget)}
                onClose={() => setRenameTarget(null)}
                folder={renameTarget}
                onSubmit={(name) => renameFolder(renameTarget.id, name)}
            />
            <ConfirmDialog
                open={Boolean(deleteTarget)}
                onClose={() => setDeleteTarget(null)}
                title="Eliminar carpeta"
                description={`Esta acción no se puede deshacer. La carpeta "${deleteTarget?.name}" debe estar vacía.`}
                onConfirm={() => deleteFolder(deleteTarget.id)}
            />
        </section>
    );
}
