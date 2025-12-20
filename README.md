# YouTube Auto Delete API

API backend para gestionar y eliminar videos de playlists de YouTube automáticamente. Construida con FastAPI siguiendo principios de Clean Architecture y Domain-Driven Design.

## 🚀 Características

-   **Autenticación OAuth con Google**: Integración completa con Google OAuth 2.0
-   **Gestión de Playlists**: Obtener y filtrar videos de playlists de YouTube
-   **Filtrado por Fechas**: Filtrar videos agregados a playlists en rangos de fechas específicos
-   **Caché Inteligente**: Sistema de caché con Redis/Valkey para optimizar rendimiento
-   **Rate Limiting**: Protección contra abuso con límites de requests por IP
-   **Arquitectura Limpia**: Separación clara de responsabilidades (Domain, Application, Infrastructure)
-   **Documentación API**: OpenAPI/Swagger automática
-   **Tests**: Suite completa de tests unitarios e integración

## 📋 Requisitos Previos

-   Python 3.11+
-   Docker y Docker Compose (para desarrollo local)
-   Cuenta de Google Cloud con OAuth 2.0 configurado
-   AWS Account (para producción con DynamoDB y ElastiCache)

## 🛠️ Instalación

### Desarrollo Local

1. **Clonar el repositorio**

```bash
git clone <repository-url>
cd playlistmaster/backend
```

2. **Configurar variables de entorno**

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

3. **Iniciar servicios con Docker Compose**

```bash
docker-compose up -d
```

Esto iniciará:

-   FastAPI en `http://localhost:8080`
-   DynamoDB Local en `http://localhost:8000`
-   DynamoDB Admin UI en `http://localhost:8001`
-   Valkey (Redis-compatible) en `localhost:6379`

4. **Instalar dependencias (desarrollo local)**

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

5. **Ejecutar la aplicación**

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Variables de Entorno

Crea un archivo `.env` con las siguientes variables:

```env
# App
APP_ENV=dev
LOG_LEVEL=INFO

# DynamoDB
TABLE_NAME=youtube-delete-app
DYNAMODB_ENDPOINT=http://localhost:8000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=fakeMyKeyId
AWS_SECRET_ACCESS_KEY=fakeSecretAccessKey

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# JWT
JWT_SECRET=your_jwt_secret_key

# Redis/Valkey
REDIS_HOST=localhost
REDIS_PORT=6379
# Para ElastiCache en producción:
# REDIS_URL=rediss://:password@endpoint.cache.amazonaws.com:6379
# REDIS_USE_TLS=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

## 📚 Documentación de la API

Una vez que la aplicación esté corriendo, accede a:

-   **Swagger UI**: `http://localhost:8080/docs`
-   **ReDoc**: `http://localhost:8080/redoc`
-   **OpenAPI JSON**: `http://localhost:8080/openapi.json`

## 🏗️ Arquitectura

Este proyecto sigue los principios de **Clean Architecture** y **Domain-Driven Design (DDD)**:

```
src/
├── api/              # Capa de presentación (FastAPI routers)
├── application/       # Servicios de aplicación (orquestación)
├── domain/           # Lógica de negocio (entidades, agregados, servicios de dominio)
├── infrastructure/   # Implementaciones técnicas (repositorios, servicios externos)
├── core/             # Configuración y utilidades centrales
├── schemas/          # DTOs y modelos de validación (Pydantic)
└── middlewares/      # Middlewares de FastAPI
```

Para más detalles, consulta [ARCHITECTURE.md](./ARCHITECTURE.md).

## 🧪 Testing

### Ejecutar todos los tests

```bash
pytest
```

### Con cobertura

```bash
pytest --cov=src --cov-report=html
```

### Tests específicos

```bash
# Tests unitarios
pytest tests/unit/

# Tests de integración
pytest tests/integration/
```

## 📦 Estructura del Proyecto

```
backend/
├── src/
│   ├── api/              # Endpoints y routers
│   ├── application/      # Servicios de aplicación
│   ├── domain/          # Lógica de negocio
│   ├── infrastructure/  # Implementaciones técnicas
│   ├── core/            # Configuración
│   ├── schemas/         # Modelos Pydantic
│   └── middlewares/     # Middlewares
├── tests/               # Tests
├── docker/              # Dockerfiles
├── scripts/             # Scripts de utilidad
├── docker-compose.yaml  # Configuración Docker Compose
├── requirements.txt     # Dependencias Python
└── pytest.ini          # Configuración pytest
```

## 🔐 Autenticación

La API usa autenticación basada en cookies HTTP-only:

1. **Login**: `POST /api/auth/exchange`

    - Intercambia código OAuth de Google por tokens
    - Establece cookie `session_token` (HTTP-only, Secure, SameSite=Strict)

2. **Endpoints protegidos**: Requieren cookie de sesión válida

    - La sesión se refresca automáticamente si es necesario

3. **Logout**: `POST /api/auth/logout`
    - Revoca tokens y elimina cookie

## 🚦 Rate Limiting

La API implementa rate limiting por IP:

-   **Por minuto**: 60 requests (configurable)
-   **Por hora**: 1000 requests (configurable)
-   **Excepciones**: Health checks (`/api/health`) no están limitados

## 💾 Persistencia

-   **DynamoDB**: Almacenamiento principal de usuarios y tokens
-   **Redis/Valkey**: Caché para optimizar respuestas de la API de YouTube

## 🔄 Flujo de Datos

```
Request → Middleware (CORS, Rate Limit) → Router → Application Service
                                                      ↓
                                          Domain Service / Aggregate
                                                      ↓
                                          Infrastructure (Repository, External API)
                                                      ↓
                                          Response
```

## 🐳 Docker

### Desarrollo

```bash
docker-compose up -d
```

### Producción

```bash
docker build -f docker/Dockerfile.prod -t playlistmaster-api .
docker run -p 8080:80 --env-file .env playlistmaster-api
```

## 📝 Scripts Útiles

### Generar OpenAPI schema

```bash
python scripts/generate_openapi.py
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## 🐛 Troubleshooting

### Redis no conecta

-   Verifica que Valkey/Redis esté corriendo: `docker ps`
-   Revisa logs: `docker-compose logs valkey`

### DynamoDB no conecta

-   Verifica que DynamoDB Local esté corriendo: `docker ps`
-   Accede al admin UI: `http://localhost:8001`

### Errores de autenticación

-   Verifica que `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` estén correctos
-   Asegúrate de que el redirect_uri esté configurado en Google Console

## 📞 Soporte

Para reportar bugs o solicitar features, abre un issue en el repositorio.

---

**Desarrollado con ❤️ usando FastAPI, Clean Architecture y DDD**
