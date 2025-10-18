# LearnIA Search API Lambda

API de búsqueda y gestión de cursos para LearnIA usando MongoDB Atlas Vector Search y Amazon Bedrock.

## Características

- **Búsqueda semántica** usando embeddings de Amazon Titan
- **MongoDB Atlas Vector Search** para búsqueda de cursos
- **PostgreSQL** para favoritos de usuarios
- **CORS** configurado para frontend
- **API RESTful** con rutas:
  - `POST /api/search` - Búsqueda semántica de cursos
  - `GET /api/courses/{id}` - Obtener curso por ID
  - `GET /api/courses/categories` - Listar categorías
  - `GET /api/courses/trending` - Cursos populares
  - `POST /api/courses/{id}/favorite` - Toggle favorito

## Requisitos Previos

1. AWS SAM CLI instalado
2. Credenciales AWS configuradas
3. MongoDB Atlas con Vector Search configurado
4. PostgreSQL RDS con tabla `user_favorites`

## Configuración

### 1. Variables de Entorno Necesarias

Edita `samconfig.toml` y configura:

```toml
parameter_overrides = [
    "Environment=dev",
    "AtlasUri=mongodb+srv://usuario:password@cluster.mongodb.net",
    "PostgresHost=learnia-postgres.criy8e4i62gn.us-east-2.rds.amazonaws.com",
    "PostgresPassword=tu-password-seguro",
    "CorsAllowOrigin=https://www.learn-ia.app"
]
```

### 2. Verificar Estructura

```
search-api-lambda/
├── src/
│   ├── search_api_lambda.py
│   ├── requirements.txt
│   └── utils/
│       ├── bedrock_client.py
│       ├── mongodb_client.py
│       └── postgres_client.py
├── layer-certs/
│   └── certs/
│       └── rds-us-east-2-bundle.pem
├── template.yaml
└── samconfig.toml
```

## Despliegue

### Build

```bash
sam build
```

### Deploy

```bash
sam deploy --guided
```

O usando samconfig.toml:

```bash
sam deploy
```

### Deploy Rápido (sin confirmación)

```bash
sam build && sam deploy --no-confirm-changeset
```

## Testing Local

```bash
sam local invoke SearchApiFunction --event events/search.json
```

Ejemplo de evento (`events/search.json`):

```json
{
  "httpMethod": "POST",
  "path": "/api/search",
  "body": "{\"query\":\"python machine learning\",\"limit\":10}"
}
```

## Endpoints Desplegados

Después del despliegue, SAM mostrará:

```
Outputs
--------
SearchApiUrl: https://xxxxx.execute-api.us-east-2.amazonaws.com
```

## Uso desde Frontend

```javascript
const response = await fetch('https://xxxxx.execute-api.us-east-2.amazonaws.com/api/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'python data science',
    limit: 12,
    filters: {
      category: 'Data Science',
      level: 'intermediate'
    }
  })
});

const data = await response.json();
console.log(data.results);
```

## Monitoreo

CloudWatch Logs: `/aws/lambda/learnia-search-api-dev`

```bash
sam logs -n SearchApiFunction --tail
```

## Troubleshooting

### Error: No module named 'pymongo'

```bash
sam build --use-container
```

### Error: SSL Certificate verify failed

Verifica que `layer-certs/certs/rds-us-east-2-bundle.pem` existe.

### Error: CORS

Verifica `CorsAllowOrigin` en `template.yaml` coincide con tu dominio frontend.

## Limpieza

```bash
sam delete
```

## Estructura de Respuestas

### POST /api/search

```json
{
  "results": [
    {
      "course_id": "...",
      "title": "Python for Data Science",
      "description": "...",
      "platform": "Coursera",
      "url": "https://...",
      "score": 0.95
    }
  ],
  "total": 10,
  "query": "python data science"
}
```

### GET /api/courses/{id}

```json
{
  "course": {
    "course_id": "...",
    "title": "...",
    "description": "...",
    "platform": "...",
    "url": "...",
    "category": "...",
    "level": "..."
  }
}
```
