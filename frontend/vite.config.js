import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        // Atado a localhost a proposito: con host:true (0.0.0.0) cualquiera en
        // la misma red WiFi puede abrir http://<tu-ip>:5173/api/perfil y leer
        // el CV y el historial de postulaciones, porque el backend no tiene
        // autenticacion. docker-compose ya publica los puertos en 127.0.0.1;
        // esto cierra la misma puerta para el modo dev.
        host: '127.0.0.1',
        port: 5173,
        proxy: {
            '/api': {
                target: process.env.VITE_API_TARGET || 'http://localhost:8000',
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
        },
    },
})