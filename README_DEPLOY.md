# Search API Lambda - Resumen de Configuración

## Estado Actual: LISTO PARA DESPLEGAR

### Archivos Completados ✅

```
search-api-lambda/
├── .github/
│   └── workflows/
│       └── deploy-search-api.yml          ✅ Workflow de GitHub Actions
├── src/
│   ├── search_api_lambda.py               ✅ Handler principal
│   ├── requirements.txt                    ✅ Dependencias Python
│   └── utils/
│       ├── bedrock_client.py               ✅ Cliente Bedrock
│       ├── mongodb_client.py               ✅ Cliente MongoDB
│       └── postgres_client.py              ✅ Cliente PostgreSQL
├── layer-certs/
│   └── certs/
│       └── rds-us-east-2-bundle.pem        ✅ Certificado SSL RDS
├── template.yaml                           ✅ SAM template completo
├── CHECKLIST.md                            ✅ Checklist de deploy
├── DEPLOYMENT.md                           ✅ Guía de despliegue
├── GITHUB_SECRETS.md                       ✅ Guía de secrets
└── README.md                               ✅ Documentación

```

---

## Pasos para Desplegar

### 1. Configurar GitHub Secrets (REQUERIDO)

Ve a GitHub: `Settings → Secrets and variables → Actions`

Agrega estos 3 secrets:

| Secret Name | Valor | Dónde obtenerlo |
|-------------|-------|-----------------|
| `ATLAS_URI` | `mongodb+srv://user:pass@cluster.mongodb.net/learnia_db` | MongoDB Atlas → Connect |
| `POSTGRES_HOST` | `learnia-postgres.criy8e4i62gn.us-east-2.rds.amazonaws.com` | RDS Console o AWS CLI |
| `POSTGRES_PASSWORD` | Tu password de PostgreSQL | Password que configuraste en RDS |

📄 Ver detalles en: **GITHUB_SECRETS.md**

---

### 2. Push al Repositorio

```bash
cd /home/raul/Documents/Proyecto_Integrador_2/Repositorios/search-api-lambda

# Verificar que estés en el repo correcto
git remote -v
# Origin debe ser: ProyectoIntegrdor2-LearnAI/search-api-lambda

# Add, commit, push
git add .
git commit -m "feat: configure search api lambda with github actions"
git push origin main
```

---

### 3. Verificar Despliegue

1. Ve a GitHub: **Actions** tab
2. Busca el workflow: `Deploy Search API Lambda`
3. Verifica que pasa todos los pasos:
   - ✅ Checkout
   - ✅ Setup Python
   - ✅ Setup SAM
   - ✅ Configure AWS credentials
   - ✅ SAM Build
   - ✅ SAM Deploy

4. Al finalizar, copia el **API URL** de los outputs

---

### 4. Obtener URL del API

```bash
aws cloudformation describe-stacks \
  --stack-name learnia-search-api-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`SearchApiUrl`].OutputValue' \
  --output text
```

O desde la consola de AWS:
- CloudFormation → Stacks → learnia-search-api-dev → Outputs

---

### 5. Actualizar Frontend

Edita: `pi2-frontend/src/config/endpoints.js`

Agrega el nuevo endpoint:

```javascript
export const LAMBDA_ENDPOINTS = {
  learningPath: 'https://yhjk0mfvgc.execute-api.us-east-2.amazonaws.com/Prod',
  courses: 'https://avouruymc3.execute-api.us-east-2.amazonaws.com/Prod',
  search: 'https://XXXXX.execute-api.us-east-2.amazonaws.com',  // ← NUEVO
  userManagement: 'https://XXXXX.execute-api.us-east-2.amazonaws.com/Prod'
};
```

---

## Testing del API

### Test 1: Búsqueda

```bash
curl -X POST https://[API-URL]/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python machine learning",
    "limit": 5,
    "filters": {
      "level": "intermediate"
    }
  }'
```

### Test 2: Categorías

```bash
curl https://[API-URL]/api/courses/categories
```

### Test 3: Trending

```bash
curl "https://[API-URL]/api/courses/trending?limit=10"
```

### Test 4: Curso por ID

```bash
curl https://[API-URL]/api/courses/COURSE_ID_HERE
```

---

## Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/search` | Búsqueda semántica con embeddings |
| GET | `/api/courses/categories` | Lista de categorías disponibles |
| GET | `/api/courses/trending` | Cursos populares/trending |
| GET | `/api/courses/{id}` | Detalle de un curso específico |
| POST | `/api/courses/{id}/favorite` | Toggle favorito (requiere user-id) |

---

## Verificación de Prerequisites

### MongoDB Atlas
```bash
# Verificar que puedes conectar
mongosh "mongodb+srv://USER:PASS@cluster.mongodb.net/learnia_db"

# Verificar que existe la colección courses
use learnia_db
db.courses.countDocuments()

# Verificar que existe el vector search index
db.courses.getSearchIndexes()
```

### PostgreSQL RDS
```sql
-- Conectar y verificar tabla user_favorites
\c postgres
\dt public.user_favorites
SELECT COUNT(*) FROM user_favorites;
```

### AWS Bedrock
```bash
# Verificar que puedes invocar el modelo
aws bedrock-runtime invoke-model \
  --model-id amazon.titan-embed-text-v2:0 \
  --body '{"inputText":"test"}' \
  --region us-east-2 \
  output.json
```

---

## Monitoreo Post-Deploy

### CloudWatch Logs

```bash
# Ver logs en tiempo real
aws logs tail /aws/lambda/learnia-search-api-dev --follow

# Buscar errores
aws logs filter-log-events \
  --log-group-name /aws/lambda/learnia-search-api-dev \
  --filter-pattern "ERROR"
```

### Métricas

- Lambda Invocations
- Duration
- Errors
- Throttles
- Concurrent Executions

Accede en: CloudWatch → Metrics → Lambda → By Function Name → learnia-search-api-dev

---

## Troubleshooting Común

### ❌ Build falla: "No module named 'pymongo'"
**Solución**: Verifica que `requirements.txt` está en `src/requirements.txt`

### ❌ Deploy falla: "Secret not found"
**Solución**: Configura los GitHub Secrets (ver GITHUB_SECRETS.md)

### ❌ Lambda timeout
**Solución**: Aumenta el timeout en `template.yaml` (actualmente 30s)

### ❌ CORS error
**Solución**: Verifica que `CorsAllowOrigin` en el workflow coincide con tu frontend

### ❌ Cannot connect to MongoDB
**Solución**: 
- Verifica que el ATLAS_URI es correcto
- Verifica whitelist de IPs en MongoDB Atlas (agrega 0.0.0.0/0 para permitir AWS Lambda)

### ❌ Cannot connect to PostgreSQL
**Solución**:
- Verifica Security Group del RDS permite tráfico desde Lambda
- Si Lambda está en VPC, verifica que tiene acceso a internet para Bedrock

---

## Próximos Pasos

Después del deploy exitoso:

1. ✅ Actualizar frontend con la nueva URL del API
2. ✅ Probar búsqueda desde la UI
3. ✅ Configurar alarmas en CloudWatch
4. ✅ Documentar endpoints en Postman
5. ✅ Agregar rate limiting si es necesario
6. ✅ Configurar monitoreo de costos

---

## Recursos Útiles

- 📄 [CHECKLIST.md](./CHECKLIST.md) - Checklist detallado de deploy
- 📄 [DEPLOYMENT.md](./DEPLOYMENT.md) - Guía completa de despliegue
- 📄 [GITHUB_SECRETS.md](./GITHUB_SECRETS.md) - Cómo configurar secrets
- 🔗 [AWS SAM Docs](https://docs.aws.amazon.com/serverless-application-model/)
- 🔗 [MongoDB Atlas Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/)

---

**¿Listo para desplegar?** 

1. Configura los 3 GitHub Secrets
2. Push a main
3. Verifica en GitHub Actions

🚀 **¡Good luck!**
