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

### Despliegue Automático con GitHub Actions

Este proyecto usa GitHub Actions para CI/CD automático.

#### 1. Configurar GitHub Secrets

En el repositorio de GitHub:
- `Settings → Secrets and variables → Actions`
- Agregar los siguientes secrets:
  - `ATLAS_URI`: Connection string de MongoDB Atlas
  - `POSTGRES_HOST`: `learnia-postgres.criy8e4i62gn.us-east-2.rds.amazonaws.com`
  - `POSTGRES_PASSWORD`: Password de PostgreSQL RDS

#### 2. Push para Deploy

```bash
git add .
git commit -m "feat: update search api"
git push origin main
```

El workflow se ejecutará automáticamente y desplegará la Lambda.

### Despliegue Manual (Opcional)

Para testing local o despliegue manual:

```bash
cd /home/raul/Documents/Proyecto_Integrador_2/Repositorios/search-api-lambda

# Build con container
sam build --use-container

# Deploy
sam deploy \
  --stack-name learnia-search-api-dev \
  --region us-east-2 \
  --s3-bucket learnia-sam-artifacts-us-east-2 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    Environment=dev \
    AtlasUri="mongodb+srv://usuario:password@cluster.mongodb.net" \
    PostgresHost="learnia-postgres.criy8e4i62gn.us-east-2.rds.amazonaws.com" \
    PostgresPassword="tu-password-postgres" \
    CorsAllowOrigin="https://www.learn-ia.app"
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
