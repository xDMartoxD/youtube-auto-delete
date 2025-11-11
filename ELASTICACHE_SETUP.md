# Configuración de AWS ElastiCache para Valkey

Esta guía explica cómo configurar la aplicación para usar AWS ElastiCache con Valkey. Valkey es un fork de Redis compatible con la API de Redis, por lo que funciona con los mismos clientes y protocolos.

## Opciones de Configuración

### Opción 1: Usando REDIS_URL (Recomendado)

La forma más simple es usar la variable de entorno `REDIS_URL`:

```bash
# Para ElastiCache con Valkey sin TLS
REDIS_URL=redis://your-elasticache-endpoint.cache.amazonaws.com:6379

# Para ElastiCache con Valkey y TLS (in-transit encryption)
REDIS_URL=rediss://your-elasticache-endpoint.cache.amazonaws.com:6379

# Para ElastiCache con Valkey y autenticación
REDIS_URL=redis://:your-password@your-elasticache-endpoint.cache.amazonaws.com:6379

# Para ElastiCache con Valkey, autenticación y TLS
REDIS_URL=rediss://:your-password@your-elasticache-endpoint.cache.amazonaws.com:6379
```

### Opción 2: Usando variables individuales

```bash
REDIS_HOST=your-elasticache-endpoint.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=your-password  # Si está habilitada la autenticación
REDIS_USE_TLS=true  # Si está habilitado in-transit encryption
REDIS_SSL_CERT_REQS=required  # 'none', 'optional', o 'required'
```

## Configuración por Entorno

### Desarrollo Local (.env)

```bash
# Para desarrollo local, puedes usar Redis local de docker-compose
# O conectar directamente a ElastiCache con Valkey
REDIS_HOST=redis
REDIS_PORT=6379
# REDIS_URL no está definida, usa host/port

# O usar directamente ElastiCache con Valkey:
# REDIS_URL=rediss://:password@your-elasticache-endpoint.cache.amazonaws.com:6379
```

### Staging/Producción (.env o variables de entorno)

```bash
# ElastiCache con Valkey endpoint (obtener de AWS Console)
REDIS_URL=rediss://:your-password@your-cluster.xxxxx.cache.amazonaws.com:6379
REDIS_USE_TLS=true
```

## Crear ElastiCache en AWS

### 1. Crear Cluster ElastiCache con Valkey

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id youtube-cache \
  --cache-node-type cache.t3.micro \
  --engine valkey \
  --num-cache-nodes 1 \
  --region us-east-1
```

### 2. Con AWS Console

1. Ve a **ElastiCache** en AWS Console
2. Click en **Create** → **Valkey cluster** (o **Redis cluster** si Valkey no está disponible como opción separada)
3. Configura:
    - **Name**: `youtube-cache`
    - **Engine**: Valkey (o Redis si Valkey no está disponible; Valkey es compatible)
    - **Node type**: `cache.t3.micro` (o mayor según necesidades)
    - **Number of replicas**: 0 (o más para alta disponibilidad)
    - **Subnet group**: Selecciona tu VPC
    - **Security groups**: Asegúrate que permita tráfico desde tu aplicación
    - **Encryption in-transit**: Habilitado (recomendado)
    - **Auth token**: Opcional pero recomendado

### 3. Obtener el Endpoint

Una vez creado, obtén el **Primary Endpoint** desde la consola de AWS.

## Configuración de Seguridad

### Security Groups

Asegúrate que el Security Group de ElastiCache permita conexiones desde tu aplicación:

```json
{
    "Type": "Custom TCP",
    "Port": 6379,
    "Source": "sg-xxxxx" // Security Group de tu aplicación
}
```

### VPC y Subnets

-   ElastiCache debe estar en la misma VPC que tu aplicación
-   O usar VPC peering si están en VPCs diferentes
-   Asegúrate que las subnets tengan rutas apropiadas

## Configuración en Kubernetes

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
    name: app-config
data:
    REDIS_URL: 'rediss://:${REDIS_PASSWORD}@your-elasticache-endpoint.cache.amazonaws.com:6379'
    REDIS_USE_TLS: 'true'
```

### Secret para Password

```yaml
apiVersion: v1
kind: Secret
metadata:
    name: redis-secret
type: Opaque
stringData:
    REDIS_PASSWORD: 'your-elasticache-auth-token'
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: backend
spec:
    template:
        spec:
            containers:
                - name: fastapi
                  env:
                      - name: REDIS_URL
                        valueFrom:
                            configMapKeyRef:
                                name: app-config
                                key: REDIS_URL
                      - name: REDIS_PASSWORD
                        valueFrom:
                            secretKeyRef:
                                name: redis-secret
                                key: REDIS_PASSWORD
```

## Verificación

### Probar Conexión

La aplicación verificará automáticamente la conexión al iniciar. Revisa los logs:

```bash
# Deberías ver:
INFO: Redis connection established
```

Si hay error:

```
WARNING: Failed to connect to Redis: ... Cache will not be available.
```

### Test Manual

```python
import asyncio
from src.core.cache import get_redis_client

async def test_connection():
    client = await get_redis_client()
    result = await client.ping()
    print(f"Connection successful: {result}")

asyncio.run(test_connection())
```

## Troubleshooting

### Error: Connection refused

-   Verifica que el Security Group permita conexiones desde tu aplicación
-   Verifica que estés usando el endpoint correcto
-   Verifica que ElastiCache esté en la misma VPC

### Error: SSL/TLS

-   Asegúrate que `REDIS_USE_TLS=true` si ElastiCache tiene encryption in-transit
-   O usa `rediss://` en lugar de `redis://` en la URL

### Error: Authentication failed

-   Verifica que el password/token sea correcto
-   Verifica que la autenticación esté habilitada en ElastiCache

### Error: Timeout

-   Verifica que las subnets tengan rutas apropiadas
-   Verifica que no haya firewalls bloqueando el tráfico
-   Considera aumentar el timeout en el cliente Redis

## Migración desde Redis Local

1. **Crear ElastiCache** en AWS
2. **Actualizar variables de entorno** con el endpoint
3. **Verificar conexión** en logs
4. **Opcional**: Migrar datos existentes (si es necesario)

## Costos

-   **cache.t3.micro**: ~$0.017/hora (~$12/mes)
-   **cache.t3.small**: ~$0.034/hora (~$24/mes)
-   **cache.t3.medium**: ~$0.068/hora (~$49/mes)

Considera usar **Reserved Instances** para ahorrar costos en producción.

## Mejores Prácticas

1. ✅ **Usar TLS/SSL** para encryption in-transit
2. ✅ **Habilitar autenticación** con auth tokens
3. ✅ **Usar Multi-AZ** para alta disponibilidad
4. ✅ **Configurar backups automáticos**
5. ✅ **Monitorear métricas** en CloudWatch
6. ✅ **Usar Parameter Store/Secrets Manager** para passwords
7. ✅ **Configurar alertas** para fallos de conexión
