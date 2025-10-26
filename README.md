## Descripción general
LearnIA Search API Lambda expone una API de búsqueda semántica y gestión de favoritos para la plataforma LearnIA. Ejecuta Python 3.11 en AWS Lambda, se despliega con AWS SAM y depende de MongoDB Atlas, PostgreSQL y AWS Bedrock Titan Embeddings.
- **Nombre**: LearnIA Search API Lambda
- **Descripción breve**: Función Lambda que orquesta búsquedas de cursos, catálogos auxiliares y favoritos.
- **Tipo de proyecto**: Lambda + API (AWS API Gateway REST con stage `Prod`).
- **Documentos clave**: `template.yaml`, `src/search_api_lambda.py`, `src/utils/`.

## Arquitectura y flujo
- API Gateway recibe peticiones HTTP y las enruta a `search_api_lambda.lambda_handler`.
- La Lambda normaliza el CORS dinámicamente y dirige la solicitud a MongoDB Atlas, PostgreSQL o AWS Bedrock según la ruta.
- MongoDB almacena el catálogo de cursos y los embeddings para búsqueda vectorial.
- AWS Bedrock Titan genera embeddings de texto para las consultas.
- PostgreSQL gestiona la tabla de favoritos por usuario.
- CloudWatch Logs y métricas personalizadas (si se habilitan) centralizan observabilidad.

### Flujo resumido
```text
Cliente → API Gateway (/Prod) → Lambda (search_api_lambda.py)
Lambda → AWS Bedrock (Titan Embeddings)
Lambda → MongoDB Atlas (catálogo de cursos)
Lambda → PostgreSQL (tabla de favoritos)
Lambda → CloudWatch Logs/Metrics
```

## Stack técnico
- Python 3.11, AWS Lambda, AWS SAM (`template.yaml`).
- AWS API Gateway REST (stage `Prod`) con CORS configurado vía parámetros.
- MongoDB Atlas (`utils/mongodb_client.py`) con agregaciones `$vectorSearch`.
- PostgreSQL gestionado con `psycopg2` y pool de conexiones (`utils/postgres_client.py`).
- AWS Bedrock Titan Embeddings vía `boto3` (`utils/bedrock_client.py`).
- Dependencias declaradas en `src/requirements.txt`.

## Estructura del proyecto
```text
.
├── template.yaml                  # Definición SAM: función, API Gateway, layer de certificados
├── layer-certs/                   # Certificados CA para conexiones SSL a RDS
├── src/
│   ├── search_api_lambda.py       # Handler principal de la API
│   ├── requirements.txt           # Dependencias de tiempo de ejecución
│   └── utils/
│       ├── bedrock_client.py      # Cliente Bedrock Titan embeddings con caché y reintentos
│       ├── mongodb_client.py      # Cliente MongoDB Atlas y consultas vectoriales
│       └── postgres_client.py     # Repositorio para favoritos en PostgreSQL
└── DEPLOYMENT_CORS_FIX.md         # Notas internas de despliegue y CORS
```

## API/Interfaces
### Base URL
- Salida `SearchApiUrl` del stack de CloudFormation (p.ej. `https://{api-id}.execute-api.{region}.amazonaws.com/Prod`).

### Endpoints
| Método | Ruta | Descripción | Notas |
| --- | --- | --- | --- |
| POST | `/api/search` | Busca cursos similares usando embeddings. | Body JSON con `query`, `limit`, `filters`. |
| GET | `/api/courses/{course_id}` | Devuelve el detalle de un curso por ID (MongoDB). | Acepta `ObjectId` o `legacy_id`. |
| GET | `/api/courses/categories` | Lista categorías con conteo. | Sin parámetros. |
| GET | `/api/courses/trending` | Cursos populares ordenados por `students_count` y `rating`. | Query `limit` (1–40, default 12). |
| GET | `/api/courses/favorites` | Lista favoritos del usuario autenticado. | Requiere `requestContext.authorizer.claims.sub` o header `x-user-id`. |
| POST | `/api/courses/{course_id}/favorite` | Añade, quita o alterna un favorito. | Body opcional `{ "action": "add" \| "remove" }`. |

## Rutas o comandos con ejemplos
```bash
# Try it: cursos trending (GET)
curl -X GET "$SEARCH_API_URL/api/courses/trending?limit=6"

# Try it: búsqueda semántica (POST)
curl -X POST "$SEARCH_API_URL/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 5, "filters": {"language": "es"}}'

# Try it: alternar favorito (POST)
curl -X POST "$SEARCH_API_URL/api/courses/COURSE_ID/favorite" \
  -H "Content-Type: application/json" \
  -H "x-user-id: USER_ID" \
  -d '{"action": "add"}'
```

## Formatos de request/response (JSON)
### `POST /api/search` (request)
```json
{
  "query": "python avanzado",
  "limit": 10,
  "filters": {
    "language": "es",
    "category": "Data Science",
    "level": "intermedio",
    "max_price": 100
  }
}
```

### `POST /api/search` (response)
```json
{
  "results": [
    {
      "course_id": "64f7a1...",
      "title": "Python para ciencia de datos",
      "description": "...",
      "url": "https://...",
      "platform": "Coursera",
      "rating": 4.8,
      "students_count": 12000,
      "language": "es",
      "level": "intermedio",
      "category": "Data Science",
      "score": 0.89
    }
  ],
  "total": 1,
  "query": "python avanzado"
}
```

### `POST /api/courses/{course_id}/favorite` (response)
```json
{
  "course_id": "64f7a1...",
  "is_favorite": true,
  "course": {
    "course_id": "64f7a1...",
    "title": "Python para ciencia de datos",
    "description": "...",
    "url": "https://..."
  }
}
```

## Códigos de error
- `400 Bad Request`: parámetros inválidos (p.ej. `query` con <3 caracteres, JSON malformado).
- `401 Unauthorized`: rutas de favoritos sin identificar al usuario.
- `404 Not Found`: curso inexistente o ruta no definida.
- `500 Internal Server Error`: fallos inesperados (con log en CloudWatch).

## Configuración y variables de entorno
| Variable | Descripción | Valor por defecto |
| --- | --- | --- |
| `LOG_LEVEL` | Nivel de logeo para la Lambda. | `INFO` |
| `ATLAS_URI` | Cadena de conexión MongoDB Atlas. | Requiere confirmación (parámetro SAM) |
| `DATABASE_NAME` | Base de datos en MongoDB. | `learnia_db` |
| `COLLECTION_NAME` | Colección de cursos en MongoDB. | `courses` |
| `ATLAS_SEARCH_INDEX` | Índice vectorial usado en `$vectorSearch`. | `default` |
| `MONGO_CONNECT_TIMEOUT_MS` | Timeout de conexión Mongo. | `10000` |
| `MONGO_SERVER_SELECTION_TIMEOUT_MS` | Timeout de selección de servidor. | `10000` |
| `EMBEDDING_MODEL` | Modelo Titan Embeddings utilizado. | `amazon.titan-embed-text-v2:0` |
| `EMBEDDING_DIM` | Dimensión esperada del embedding. | `1024` |
| `AWS_REGION` | Región para Bedrock Runtime. | `us-east-2` |
| `POSTGRES_HOST` | Hostname del RDS PostgreSQL. | Requiere confirmación (parámetro SAM) |
| `POSTGRES_PORT` | Puerto de PostgreSQL. | `5432` |
| `POSTGRES_DB` | Base de datos objetivo. | `postgres` |
| `POSTGRES_USER` | Usuario de conexión. | `postgres` |
| `POSTGRES_PASSWORD` | Password de conexión. | Requiere confirmación (parámetro SAM) |
| `POSTGRES_POOL_MIN` | Conexiones mínimas en el pool. | `1` |
| `POSTGRES_POOL_MAX` | Conexiones máximas en el pool. | `5` |
| `FAVORITES_TABLE` | Tabla de favoritos en PostgreSQL. | `user_favorites` |
| `DB_SSL` | Habilita SSL hacia RDS. | `true` |
| `DB_CA_PATH` | Ruta del bundle de certificados en la layer. | `/opt/certs/rds-us-east-2-bundle.pem` |
| `CORS_ORIGIN` | Lista separada por comas de orígenes permitidos. | `https://www.learn-ia.app` |

## Desarrollo local
### Prerrequisitos
- Python 3.11 y `pip`.
- Credenciales AWS con permiso para `bedrock:InvokeModel` (solo si se invoca Bedrock en local).
- Acceso de red a MongoDB Atlas y PostgreSQL equivalentes al entorno.

### Pasos mínimos
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
export LOG_LEVEL=DEBUG  # Ajustar variables necesarias (ver tabla anterior)
python - <<'PY'
from search_api_lambda import lambda_handler
event = {"httpMethod": "GET", "path": "/api/courses/trending"}
print(lambda_handler(event, None))
PY
```

## Pruebas
- Requiere confirmación. No existen pruebas automatizadas en el repositorio; se sugiere incorporar unit tests para `utils/` y pruebas contractuales de los endpoints.

## Despliegue
### Con AWS SAM
```bash
sam build
sam deploy \
  --stack-name learnia-search-api \
  --parameter-overrides \
    Environment=prod \
    CorsAllowOrigin=https://www.learn-ia.app \
    AtlasUri="..." \
    PostgresHost="..." \
    PostgresPassword="..." \
  --capabilities CAPABILITY_IAM
```
- `Environment` controla el sufijo del nombre de la función (`learnia-search-api-${Environment}`).
- `template.yaml` crea también la layer `CertificatesLayer` necesaria para SSL con RDS.
- Si se despliega desde CI/CD, verificar secretos y permisos de IAM del rol executor.

## Observabilidad
- Logs estructurados via `logging` en CloudWatch (`/aws/lambda/learnia-search-api-*`).
- Política IAM permite `cloudwatch:PutMetricData`; si se requiere, instrumentar métricas personalizadas en el handler.
- Ajustar `LOG_LEVEL` para depuración puntual; preferir `INFO` en producción.

## Manejo de errores y validaciones
- `SearchApiError` encapsula errores controlados con `status_code` específico.
- Validaciones clave: longitud mínima de `query`, parámetros numéricos (`limit`), acciones permitidas (`add`, `remove`).
- Respuestas consistentemente en JSON con mensajes de error localizados en español.
- Las rutas OPTIONS responden `204` con encabezados CORS generados dinámicamente.

## Solución de problemas
### FAQ
- **¿Sigo recibiendo 404 en `/api/*`?** Asegura que estés llamando a la URL con el prefijo `/Prod` o actualiza el stage en SAM si migras a `$default`. Requiere confirmación en entorno.
- **¿Error 401 al consultar favoritos?** Comprueba que el request incluya `x-user-id` (o que el authorizer propague `sub`) y que la Lambda corra en un entorno con authorizer configurado.
- **¿`OperationalError` conectando a PostgreSQL?** Valida `POSTGRES_HOST`, `POSTGRES_PASSWORD` y que la cadena incluya acceso SSL si `DB_SSL=true`. Revisa que la layer `layer-certs` esté publicada.
- **¿Timeouts o fallos en Bedrock?** Confirmar permisos `bedrock:InvokeModel` y la región (`AWS_REGION`) compatible con Titan (`us-east-2`). El cliente reintenta hasta 4 veces antes de propagar el error.
- **¿Errores CORS en el cliente?** Actualiza `CORS_ORIGIN` (separado por comas) para incluir los nuevos dominios y redepliega. Verifica también que el frontend envíe encabezados soportados.

## Seguridad
- Credenciales y URIs sensibles (`ATLAS_URI`, `POSTGRES_PASSWORD`) se inyectan como parámetros SAM; no deben versionarse.
- La Lambda usa principios de mínimo privilegio: políticas limitadas a `AWSLambdaBasicExecutionRole`, `bedrock:InvokeModel` para el modelo Titan especificado y `cloudwatch:PutMetricData`.
- Conexiones a RDS forzadas sobre SSL (`DB_SSL=true`) y certificados provistos en `layer-certs/`.
- CORS restringido mediante `CORS_ORIGIN`, normalizado para evitar orígenes no autorizados; ajustar antes de incorporar nuevos clientes.

## Esquema de datos
### PostgreSQL (`user_favorites`)
```sql
CREATE TABLE user_favorites (
  favorite_id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  mongodb_course_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT user_favorites_unique UNIQUE (user_id, mongodb_course_id)
);
```

### MongoDB (colección `courses`)
- Campos esperados: `_id`, `title`, `description`, `url`, `platform`, `rating`, `duration`, `price`, `language`, `category`, `level`, `students_count`, `embedding` y metadatos opcionales (`embedding_model`, `embedding_dim`, `processed_at`).
- Índice vectorial `ATLAS_SEARCH_INDEX` para `$vectorSearch`. Detalles adicionales requieren confirmación en Atlas.

## Licencia
- Por definir.

## Notas y próximos pasos
- Completar estrategia de pruebas automatizadas y documentación de authorizers/CI.
- Confirmar valores definitivos de parámetros sensibles y documentar pipeline de despliegue (GitHub Actions u otro).
- Revisar si se migrará el stage de API Gateway a `$default` para simplificar rutas y alinear con `DEPLOYMENT_CORS_FIX.md`.
