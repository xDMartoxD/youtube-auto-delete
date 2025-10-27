# YouTube Watch Later API

## 🎯 **Funcionalidad Watch Later**

La playlist "Watch Later" es una playlist especial de YouTube que permite a los usuarios guardar videos para ver más tarde. Esta API proporciona endpoints para interactuar con esta playlist.

## 📋 **Endpoints Disponibles**

### **1. Obtener Videos de Watch Later**

```http
GET /api/youtube/watch-later
```

**Parámetros de Query:**

-   `max_results` (int, opcional): Número máximo de resultados (1-50, default: 25)
-   `page_token` (string, opcional): Token de página para paginación

**Respuesta:**

```json
{
  "items": [
    {
      "id": "playlist_item_id",
      "snippet": {
        "title": "Video Title",
        "description": "Video description",
        "thumbnails": {...},
        "resourceId": {
          "kind": "youtube#video",
          "videoId": "video_id"
        }
      },
      "contentDetails": {
        "videoId": "video_id",
        "startAt": "0",
        "endAt": "0",
        "note": ""
      }
    }
  ],
  "total_results": 50,
  "next_page_token": "next_token",
  "prev_page_token": null,
  "page_info": {
    "totalResults": 50,
    "resultsPerPage": 25
  }
}
```

### **2. Información de Watch Later**

```http
GET /api/youtube/watch-later/info
```

**Respuesta:**

```json
{
  "playlist_id": "WL",
  "title": "Watch Later",
  "description": "Videos saved to watch later",
  "item_count": 25,
  "snippet": {
    "title": "Watch Later",
    "description": "Videos saved to watch later",
    "thumbnails": {...}
  }
}
```

### **3. Agregar Video a Watch Later**

```http
POST /api/youtube/watch-later/add/{video_id}
```

**Parámetros:**

-   `video_id` (string): ID del video de YouTube a agregar

**Respuesta:**

```json
{
    "success": true,
    "playlist_item_id": "playlist_item_id",
    "video_id": "video_id",
    "message": "Video added to Watch Later"
}
```

### **4. Eliminar Video de Watch Later**

```http
DELETE /api/youtube/watch-later/remove/{playlist_item_id}
```

**Parámetros:**

-   `playlist_item_id` (string): ID del item en la playlist (no el video_id)

**Respuesta:**

```json
{
    "success": true,
    "playlist_item_id": "playlist_item_id",
    "message": "Video removed from Watch Later"
}
```

## 🔧 **Características Técnicas**

### **Playlist Especial**

-   ✅ **ID Fijo**: `WL` - Siempre el mismo para todos los usuarios
-   ✅ **Acceso Directo**: No requiere buscar en playlists del usuario
-   ✅ **Paginación**: Soporte completo para navegación de páginas
-   ✅ **CRUD Completo**: Crear, leer, actualizar y eliminar

### **Autenticación**

-   ✅ **Session Middleware**: Requiere autenticación válida
-   ✅ **Token Refresh**: Manejo automático de tokens expirados
-   ✅ **User Context**: Acceso al contexto del usuario autenticado

### **Manejo de Errores**

-   ✅ **Validación**: Parámetros validados con Pydantic
-   ✅ **HTTP Status**: Códigos de estado apropiados
-   ✅ **Error Messages**: Mensajes descriptivos de error

## 📝 **Ejemplos de Uso**

### **Obtener Primera Página**

```bash
curl -X GET "http://localhost:8080/api/youtube/watch-later?max_results=10" \
  -H "Cookie: session_token=your_session_token"
```

### **Navegar a Siguiente Página**

```bash
curl -X GET "http://localhost:8080/api/youtube/watch-later?max_results=10&page_token=next_token" \
  -H "Cookie: session_token=your_session_token"
```

### **Agregar Video**

```bash
curl -X POST "http://localhost:8080/api/youtube/watch-later/add/dQw4w9WgXcQ" \
  -H "Cookie: session_token=your_session_token"
```

### **Eliminar Video**

```bash
curl -X DELETE "http://localhost:8080/api/youtube/watch-later/remove/playlist_item_id" \
  -H "Cookie: session_token=your_session_token"
```

## 🚀 **Implementación en Frontend**

### **JavaScript/TypeScript**

```typescript
class WatchLaterAPI {
    private baseUrl = 'http://localhost:8080/api/youtube'

    async getWatchLater(maxResults = 25, pageToken?: string) {
        const params = new URLSearchParams({
            max_results: maxResults.toString(),
            ...(pageToken && { page_token: pageToken }),
        })

        const response = await fetch(`${this.baseUrl}/watch-later?${params}`, {
            credentials: 'include', // Para enviar cookies
        })

        return response.json()
    }

    async addToWatchLater(videoId: string) {
        const response = await fetch(
            `${this.baseUrl}/watch-later/add/${videoId}`,
            {
                method: 'POST',
                credentials: 'include',
            }
        )

        return response.json()
    }

    async removeFromWatchLater(playlistItemId: string) {
        const response = await fetch(
            `${this.baseUrl}/watch-later/remove/${playlistItemId}`,
            {
                method: 'DELETE',
                credentials: 'include',
            }
        )

        return response.json()
    }
}
```

### **React Hook**

```typescript
import { useState, useEffect } from 'react'

export const useWatchLater = () => {
    const [videos, setVideos] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const fetchWatchLater = async (maxResults = 25, pageToken?: string) => {
        setLoading(true)
        try {
            const response = await fetch(
                `/api/youtube/watch-later?max_results=${maxResults}${
                    pageToken ? `&page_token=${pageToken}` : ''
                }`,
                {
                    credentials: 'include',
                }
            )
            const data = await response.json()
            setVideos(data.items)
        } catch (err) {
            setError(err)
        } finally {
            setLoading(false)
        }
    }

    return { videos, loading, error, fetchWatchLater }
}
```

## ⚠️ **Consideraciones Importantes**

### **Diferencias con Playlists Normales**

-   ❌ **No se puede crear/eliminar** - Es una playlist del sistema
-   ❌ **ID fijo** - Siempre es `WL`
-   ❌ **No metadata personalizada** - Título y descripción fijos
-   ✅ **CRUD de videos** - Se pueden agregar/eliminar videos

### **Limitaciones de la API**

-   🔒 **Autenticación requerida** - Todos los endpoints requieren sesión válida
-   📊 **Paginación obligatoria** - No se puede obtener todos los videos de una vez
-   ⏱️ **Rate limiting** - Respeta los límites de YouTube API
-   🔄 **Token refresh** - Manejo automático de tokens expirados

### **Mejores Prácticas**

-   ✅ **Usar paginación** - No cargar todos los videos de una vez
-   ✅ **Manejar errores** - Implementar retry logic para fallos de red
-   ✅ **Cache local** - Guardar resultados para mejorar UX
-   ✅ **Loading states** - Mostrar indicadores de carga

## 🎯 **Casos de Uso Comunes**

1. **📱 App de Watch Later**: Lista de videos guardados para ver más tarde
2. **🔄 Sincronización**: Sincronizar con la playlist de YouTube
3. **📊 Analytics**: Analizar qué videos se guardan más
4. **🗑️ Auto-delete**: Implementar lógica de eliminación automática
5. **📋 Gestión**: Herramientas para gestionar la lista de Watch Later

## 🔗 **Enlaces Relacionados**

-   [YouTube Data API - PlaylistItems](https://developers.google.com/youtube/v3/docs/playlistItems)
-   [YouTube Data API - Playlists](https://developers.google.com/youtube/v3/docs/playlists)
-   [FastAPI Documentation](https://fastapi.tiangolo.com/)
-   [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
