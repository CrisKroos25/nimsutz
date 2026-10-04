import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    Folder as FolderIcon,
    FolderPlus,
    Pencil,
    Trash2,
    Loader2,
    FileText,
    Image as ImageIcon,
    File as FileGenericIcon,
    Search,
    List,
    LayoutGrid,
    Upload,
} from 'lucide-react';
import { useFiles } from '@features/files/hooks/useFiles';
import { useAuth } from '@shared/auth/AuthContext';
import Table from '@shared/components/Table/Table';
import FileDetails from '../components/FileDetails';
import FolderFormModal from '@features/files/components/FolderFormModal';
import ConfirmDialog from '@features/files/components/ConfirmDialog';
import UploadPanel from '@features/files/components/UploadPanel/UploadPanel';
import FileActions from '@features/files/components/FileActions/FileActions';


import Button from '@shared/components/Button/Button';
import Badge from '@shared/components/Badge/Badge';
import styles from './FilePages.module.css';

function formatBytes(bytes) {
    if (!bytes || bytes <= 0 || isNaN(Number(bytes))) return '0 B';
    const num = Number(bytes);
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(
        Math.floor(Math.log(num) / Math.log(1024)),
        units.length - 1,
    );
    if (exponent < 0) return '0 B';
    const value = num / 1024 ** exponent;
    return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function formatDate(isoString) {
    if (!isoString) return '—';
    try {
        const d = new Date(isoString);
        if (isNaN(d.getTime())) return '—';
        return d.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
        });
    } catch {
        return '—';
    }
}

function getFileTypeInfo(contentType, fileName = '') {
    const safeName = String(fileName || '');
    const ext = safeName.split('.').pop()?.toUpperCase() || '';
    const safeType = String(contentType || '').toLowerCase();

    if (safeType.includes('pdf') || ext === 'PDF') {
        return { label: 'PDF', icon: FileText, className: styles.typePdf };
    }
    if (safeType.includes('presentation') || ['PPT', 'PPTX'].includes(ext)) {
        return {
            label: ext || 'PPTX',
            icon: FileText,
            className: styles.typePpt,
        };
    }
    if (
        safeType.includes('image') ||
        ['PNG', 'JPG', 'JPEG', 'WEBP', 'SVG'].includes(ext)
    ) {
        return {
            label: ext || 'IMG',
            icon: ImageIcon,
            className: styles.typeImage,
        };
    }
    if (safeType.includes('word') || ['DOC', 'DOCX'].includes(ext)) {
        return { label: 'DOCX', icon: FileText, className: styles.typeDoc };
    }
    if (
        safeType.includes('spreadsheet') ||
        ['XLS', 'XLSX', 'CSV'].includes(ext)
    ) {
        return {
            label: ext || 'XLSX',
            icon: FileText,
            className: styles.typeExcel,
        };
    }
    if (safeType.includes('zip') || ['ZIP', 'RAR', 'TAR', 'GZ'].includes(ext)) {
        return {
            label: ext || 'ZIP',
            icon: FileText,
            className: styles.typeZip,
        };
    }
    return {
        label: ext || 'FILE',
        icon: FileGenericIcon,
        className: styles.typeDefault,
    };
}

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

export function FilesPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const folderId = Number(searchParams.get('folder')) || null;
    const { folders, files, folderIndex, loading, error, reload, createFolder, renameFolder, deleteFolder } = useFiles(folderId);
    const { user } = useAuth();
    const [createOpen, setCreateOpen] = useState(false);
    const [renameTarget, setRenameTarget] = useState(null);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [sort, setSort] = useState('recent');
    const [kind, setKind] = useState('all');
    const [view, setView] = useState('list');
    const [selectedId, setSelectedId] = useState(null);
    const breadcrumb = buildBreadcrumb(folderIndex, folderId);
    const safeFiles = Array.isArray(files) ? files : [];
    const selected = !loading && !error ? safeFiles.find(file => file.id === selectedId) : null;
    const matches = name => name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
    const compare = (a, b) => sort === 'name'
        ? (a.name || a.original_name).localeCompare(b.name || b.original_name, 'es')
        : new Date(b.updated_at) - new Date(a.updated_at);
    const visibleFolders = (Array.isArray(folders) ? folders : []).filter(folder => matches(folder.name)).sort(compare);
    const visibleFiles = safeFiles.filter(file => matches(file.original_name) && (kind === 'all' || (kind === 'images' ? file.content_type.startsWith('image/') : !file.content_type.startsWith('image/')))).sort(compare);
    function navigateFolder(id) {
        setSelectedId(null);
        setQuery('');
        setSearchParams(id == null ? {} : { folder: String(id) });
    }
    function fileName(file) {
        const type = getFileTypeInfo(file.content_type, file.original_name);
        return <button className={styles.fileButton} onClick={() => setSelectedId(file.id)} aria-pressed={selected?.id === file.id} aria-label={'Ver detalles de ' + file.original_name}>
            <span className={styles.iconBadge + ' ' + type.className}>{type.label}</span>
            <span className={styles.nameMeta}><span className={styles.fileName}>{file.original_name}</span><span className={styles.muted}>{folderIndex.get(file.folder)?.name || 'Carpeta'}</span></span>
        </button>;
    }
    const columns = [
        { key: 'original_name', label: 'Nombre', render: fileName },
        { key: 'size_bytes', label: 'Tamaño', render: file => formatBytes(file.size_bytes) },
        { key: 'updated_at', label: 'Fecha', render: file => formatDate(file.updated_at) },
        { key: 'owner', label: 'Propietario', render: () => <span title={user?.email}>Tú</span> },
        { key: 'status', label: 'Estado', render: () => <Badge tone="success">Disponible</Badge> },
        { key: 'actions', label: 'Acciones', render: file => <FileActions file={file} onChanged={reload} /> },
    ];
    return <section className={styles.page} aria-labelledby="files-title">
        <div className={styles.explorer}>
            <div className={styles.heading}>
                <div><nav aria-label="Ruta de carpetas" className={styles.breadcrumb}>
                    <button onClick={() => navigateFolder(null)}>Mis archivos</button>
                    {breadcrumb.map(crumb => <span key={crumb.id}> / <button onClick={() => navigateFolder(crumb.id)}>{crumb.name}</button></span>)}
                </nav><h1 id="files-title">{breadcrumb.at(-1)?.name || 'Mis archivos'}</h1></div>
                <div className={styles.actions}>
                    <Button variant="secondary" onClick={() => setCreateOpen(true)}><FolderPlus size={16} />Nueva carpeta</Button>
                    <Button disabled={folderId == null} title={folderId == null ? 'Abre una carpeta para subir archivos' : undefined} onClick={() => setUploadOpen(true)}><Upload size={16} />Subir archivo</Button>
                </div>
            </div>
            <div className={styles.toolbar}>
                <label className={styles.search}><Search size={16} aria-hidden="true" /><input type="search" aria-label="Buscar en esta carpeta" placeholder="Buscar archivos y carpetas…" value={query} onChange={event => setQuery(event.target.value)} /></label>
                <select aria-label="Tipo de archivo" value={kind} onChange={event => setKind(event.target.value)}><option value="all">Todos los tipos</option><option value="images">Imágenes</option><option value="documents">Documentos</option></select>
                <select aria-label="Ordenar contenido" value={sort} onChange={event => setSort(event.target.value)}><option value="recent">Más reciente</option><option value="name">Nombre A–Z</option></select>
                <div className={styles.viewToggle} role="group" aria-label="Vista de archivos">
                    <button aria-label="Vista de lista" aria-pressed={view === 'list'} onClick={() => setView('list')}><List size={16} /></button>
                    <button aria-label="Vista de cuadrícula" aria-pressed={view === 'grid'} onClick={() => setView('grid')}><LayoutGrid size={16} /></button>
                </div>
            </div>
            {folderId == null && <p className={styles.muted}>Abre una carpeta para subir y consultar sus archivos.</p>}
            {error && <div className={styles.banner} role="alert">{error} <Button variant="ghost" onClick={reload}>Reintentar</Button></div>}
            <section aria-labelledby="folders-heading"><h2 className={styles.sectionTitle} id="folders-heading">Carpetas</h2>
                {loading ? <p role="status" className={styles.emptyState}><Loader2 size={20} /> Cargando carpetas…</p> : !error && <div className={styles.folderGrid}>
                    {visibleFolders.map(folder => <article className={styles.folderCard} key={folder.id}>
                        <button className={styles.folderButton} onClick={() => navigateFolder(folder.id)}><FolderIcon size={22} fill="currentColor" /><strong title={folder.name}>{folder.name}</strong><span>{formatDate(folder.updated_at)}</span></button>
                        <div className={styles.folderActions}><button aria-label={'Renombrar ' + folder.name} onClick={() => setRenameTarget(folder)}><Pencil size={14} /></button><button aria-label={'Eliminar ' + folder.name} onClick={() => setDeleteTarget(folder)}><Trash2 size={14} /></button></div>
                    </article>)}
                    {visibleFolders.length === 0 && <p className={styles.muted}>{query ? 'No hay carpetas que coincidan.' : 'No hay subcarpetas en esta ubicación.'}</p>}
                </div>}
            </section>
            <section className={styles.filesSection} aria-labelledby="documents-heading"><h2 className={styles.sectionTitle} id="documents-heading">Archivos</h2>
                {view === 'list' || loading || error || visibleFiles.length === 0 ? <Table columns={columns} rows={visibleFiles} caption="Archivos de la carpeta actual" loading={loading} error={error} emptyMessage={query || kind !== 'all' ? 'No hay archivos que coincidan con los filtros.' : 'No hay archivos en esta ubicación.'} /> : <div className={styles.fileGrid}>
                    {visibleFiles.map(file => <article key={file.id} className={styles.fileCard}>{fileName(file)}<p className={styles.muted}>{formatBytes(file.size_bytes)} · {formatDate(file.updated_at)}</p><div className={styles.cardFooter}><Badge tone="success">Disponible</Badge><FileActions file={file} onChanged={reload} /></div></article>)}
                </div>}
            </section>
        </div>
        {selected && <FileDetails key={selected.id} file={selected} folderName={folderIndex.get(selected.folder)?.name} owner={user?.email} formatBytes={formatBytes} formatDate={formatDate} onClose={() => setSelectedId(null)} onChanged={reload} />}
        <FolderFormModal open={createOpen} onClose={() => setCreateOpen(false)} onSubmit={createFolder} />
        <FolderFormModal open={Boolean(renameTarget)} onClose={() => setRenameTarget(null)} folder={renameTarget} onSubmit={name => renameFolder(renameTarget.id, name)} />
        <ConfirmDialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} title="Eliminar carpeta" description={'Esta acción no se puede deshacer. La carpeta "' + (deleteTarget?.name || '') + '" debe estar vacía.'} onConfirm={() => deleteFolder(deleteTarget.id)} />
        {uploadOpen && <UploadPanel folderId={folderId} onCompleted={reload} onClose={() => setUploadOpen(false)} />}
    </section>;
}
