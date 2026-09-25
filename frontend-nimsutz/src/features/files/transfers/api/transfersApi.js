import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: { 'Content-Type': 'application/json' }
});

export const transfersApi = {
    solicitarCarga: (datosArchivo) => api.post('/archivos/solicitar-carga/', datosArchivo),
    confirmarCarga: (archivoId) => api.post(`/archivos/${archivoId}/confirmar/`),
    solicitarDescarga: (archivoId) => api.get(`/archivos/${archivoId}/descargar/`),
    moverAPapelera: (archivoId) => api.delete(`/archivos/${archivoId}/`)
};