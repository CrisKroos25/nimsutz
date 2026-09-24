import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const trashApi = {
    // Obtiene el listado de archivos que están en la papelera
    obtenerPapelera: async () => {
        const response = await apiClient.get('/papelera/');
        return response.data;
    },

    // Restaura un archivo a su carpeta original o raíz[cite: 6]
    restaurarArchivo: async (archivoId) => {
        const response = await apiClient.post(`/papelera/${archivoId}/restaurar/`);
        return response.data;
    },

    // Elimina definitivamente el archivo de MinIO y libera cuota (requiere confirmación)[cite: 1, 6]
    eliminarDefinitivo: async (archivoId) => {
        const response = await apiClient.delete(`/papelera/${archivoId}/eliminar-definitivo/`);
        return response.data;
    }
};