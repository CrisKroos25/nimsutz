/* Hooks del modulo (useFiles). Combinan api/ con estado de React.

   Alcance de A: navegar y organizar carpetas, y mostrar el listado de
   archivos de la carpeta actual (solo lectura). Subir, descargar,
   enviar a papelera, restaurar y eliminar definitivo son de B: ese
   estado y esas peticiones viven en los hooks de B (transfers/trash),
   no aqui. */
import { useCallback, useEffect, useState } from 'react';
import * as filesApi from '../api/filesApi';

/**
 * Hook del explorador: lista carpetas y archivos de "folderId" (null = raíz)
 * y expone las acciones de organización: crear, renombrar y eliminar
 * carpeta. "reload" se pasa a los componentes de B (UploadPanel.onCompleted,
 * FileActions.onChanged) para que el listado se refresque después de que
 * ellos suban, descarguen o envíen un archivo a la papelera.
 *
 * También trae "folderIndex": un mapa id -> {id, name, parent} de TODAS
 * las carpetas del usuario, usado para reconstruir la ruta de migas de
 * pan a partir de datos reales del servidor, en vez de llevar la cuenta
 * a mano con los clics del usuario (eso se desincroniza con el botón
 * "atrás" del navegador o al recargar la página).
 */
export function useFiles(folderId) {
    const [folders, setFolders] = useState([]);
    const [files, setFiles] = useState([]);
    const [folderIndex, setFolderIndex] = useState(new Map());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const reload = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // A nivel raíz no hay archivos posibles: todo archivo pertenece
            // siempre a una carpeta (el modelo File.folder no es nulo).
            const [folderList, fileList, allFolders] = await Promise.all([
                filesApi.listFolders(folderId),
                folderId == null ? Promise.resolve([]) : filesApi.listFiles(folderId),
                filesApi.listAllFolders(),
            ]);
            setFolders(folderList);
            setFiles(fileList);
            setFolderIndex(new Map(allFolders.map((folder) => [folder.id, folder])));
        } catch (err) {
            setError(err.message || 'No se pudo cargar el contenido de la carpeta.');
        } finally {
            setLoading(false);
        }
    }, [folderId]);

    useEffect(() => {
        reload();
    }, [reload]);

    async function createFolder(name) {
        await filesApi.createFolder({ parent: folderId, name });
        await reload();
    }

    async function renameFolder(id, name) {
        await filesApi.renameFolder(id, name);
        await reload();
    }

    async function deleteFolder(id) {
        await filesApi.deleteFolder(id);
        await reload();
    }

    return {
        folders,
        files,
        folderIndex,
        loading,
        error,
        reload,
        createFolder,
        renameFolder,
        deleteFolder,
    };
}
