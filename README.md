# Extension — LinkedIn Job Scraper

## Instalación en Chrome (desde WSL)

Los archivos de la extensión viven en tu WSL pero Chrome corre en Windows.
Tienes que copiar (o acceder) la carpeta desde Windows.

### Opción A — Ruta UNC (más fácil)
En Chrome, ve a `chrome://extensions/` → "Cargar descomprimida" → navega a:
```
\\wsl$\Ubuntu\home\<tu_usuario>\job-tracker\extension
```

### Opción B — Copiar a Windows
```bash
cp -r ~/job-tracker/extension /mnt/c/Users/<TuUsuario>/Desktop/job-tracker-extension
```
Luego en Chrome → "Cargar descomprimida" → elige esa carpeta.

---

## Íconos requeridos
Chrome requiere los íconos declarados en manifest.json.
Genera 3 PNGs placeholder con este comando:

```bash
cd ~/job-tracker/extension
# Requiere ImageMagick
sudo apt install imagemagick -y
convert -size 16x16 xc:'#00c9a7' icons/icon16.png
convert -size 48x48 xc:'#00c9a7' icons/icon48.png
convert -size 128x128 xc:'#00c9a7' icons/icon128.png
```

---

## Flujo de uso

1. Abre `linkedin.com/jobs/search` con tu string de búsqueda
2. Deja que cargue la lista de resultados (panel izquierdo)
3. Click en el ícono de la extensión → **Extraer ofertas**
4. La extensión hace click en cada tarjeta con delay de 1.5s
5. Al terminar, descarga automáticamente `raw_data/linkedin_YYYYMMDD_HHMMSS.json`
6. Mueve ese JSON a `~/job-tracker/raw_data/`
7. Ejecuta `./buscar.sh --importar` para procesarlo

---

## Estructura de cada oferta en el JSON

```json
{
  "titulo": "Senior Frontend Engineer",
  "empresa": "Acme Corp",
  "ubicacion": "Colombia (Remoto)",
  "descripcion": "...",
  "link": "https://www.linkedin.com/jobs/view/1234567890",
  "extraido_en": "2026-06-22T10:30:00.000Z"
}
```

---

## Notas

- **Selectores DOM**: LinkedIn cambia su estructura periódicamente.
  Si deja de funcionar, inspecciona el elemento en DevTools y actualiza los selectores en `content.js`.
- **Límite recomendado**: máximo 100 tarjetas por sesión.
- **Permisos requeridos**: `activeTab`, `scripting`, `storage`, `downloads`.