import process from 'node:process';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [
        react({
            babel: {
                plugins: [['babel-plugin-react-compiler']],
            },
        }),
    ],
    server: {
        host: '0.0.0.0',
        watch: {
            usePolling: true,
        },
    },
    resolve: {
        alias: {
            '@': path.resolve(import.meta.dirname, './src'),
            '@features': path.resolve(import.meta.dirname, './src/features'),
            '@shared': path.resolve(import.meta.dirname, './src/shared'),
            '@layouts': path.resolve(import.meta.dirname, './src/layouts'),
        },
    },
});
