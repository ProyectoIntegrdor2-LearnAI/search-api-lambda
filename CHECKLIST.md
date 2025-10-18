# Checklist de Despliegue - Search API Lambda

## Pre-Despliegue

### Configuración
- [x] `template.yaml` completo con parámetros
- [x] `samconfig.toml` creado
- [ ] Configurar valores en `samconfig.toml`:
  - [ ] `AtlasUri` (MongoDB connection string)
  - [ ] `PostgresHost` (RDS endpoint)
  - [ ] `PostgresPassword` (RDS password)
  - [ ] `CorsAllowOrigin` (frontend URL)

### Archivos Requeridos
- [x] `src/search_api_lambda.py`
- [x] `src/requirements.txt`
- [x] `src/utils/bedrock_client.py`
- [x] `src/utils/mongodb_client.py`
- [x] `src/utils/postgres_client.py`
- [x] `layer-certs/certs/rds-us-east-2-bundle.pem`

### Base de Datos
- [x] Tabla `user_favorites` existe en PostgreSQL
- [ ] MongoDB Atlas Vector Search index "default" configurado
- [ ] Colección `courses` tiene datos

### Permisos AWS
- [ ] Rol IAM tiene permisos para Bedrock (titan-embed-text-v2:0)
- [ ] Security Group permite conexión a RDS desde Lambda
- [ ] VPC configurado correctamente (si aplica)

## Despliegue

```bash
# 1. Editar samconfig.toml con valores reales
nano samconfig.toml

# 2. Build
cd /home/raul/Documents/Proyecto_Integrador_2/Repositorios/search-api-lambda
sam build

# 3. Deploy
sam deploy --guided

# O sin confirmación:
sam deploy
```

## Post-Despliegue

### Verificación
- [ ] Lambda desplegada exitosamente
- [ ] API Gateway creado
- [ ] URL del API obtenida de Outputs
- [ ] Logs de CloudWatch funcionando

### Testing
```bash
# Test básico
curl -X POST https://[API-URL]/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"python","limit":5}'

# Test categorías
curl https://[API-URL]/api/courses/categories

# Test trending
curl https://[API-URL]/api/courses/trending?limit=10
```

### Integración Frontend
- [ ] Actualizar `src/config/endpoints.js` con nueva URL
- [ ] Probar búsqueda desde frontend
- [ ] Verificar CORS funciona correctamente
- [ ] Probar toggle de favoritos

## Valores Necesarios

Consigue estos valores antes de desplegar:

1. **MongoDB Atlas URI**:
   ```
   MongoDB Atlas → Clusters → Connect → Connection String
   ```

2. **PostgreSQL Host**:
   ```bash
   aws rds describe-db-instances --query 'DBInstances[?DBInstanceIdentifier==`learnia-postgres`].Endpoint.Address' --output text
   ```
   Resultado: `learnia-postgres.criy8e4i62gn.us-east-2.rds.amazonaws.com`

3. **PostgreSQL Password**: (el que configuraste al crear RDS)

4. **CORS Origin**: `https://www.learn-ia.app`

## Comandos Útiles

```bash
# Ver logs en tiempo real
sam logs -n SearchApiFunction --tail

# Ver métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=learnia-search-api-dev \
  --start-time 2025-10-18T00:00:00Z \
  --end-time 2025-10-18T23:59:59Z \
  --period 3600 \
  --statistics Sum

# Actualizar solo código (sin cambios en template)
sam build && sam deploy --no-confirm-changeset

# Eliminar stack completo
sam delete
```

## Troubleshooting

### Lambda no puede conectar a RDS
- Verificar Security Group permite tráfico desde Lambda
- Verificar Lambda está en misma VPC que RDS
- Verificar subnets tienen route a internet (para Bedrock)

### CORS errors
- Verificar `CorsAllowOrigin` en template.yaml
- Verificar frontend usa URL correcta
- Verificar headers en respuesta Lambda

### Embedding errors
- Verificar región us-east-2 tiene Bedrock Titan disponible
- Verificar permisos IAM para bedrock:InvokeModel
- Verificar timeout suficiente (30s)

## Próximos Pasos

Después de desplegar exitosamente:

1. Actualizar frontend con nueva URL del API
2. Configurar monitoreo en CloudWatch
3. Configurar alarmas para errores
4. Documentar endpoints en Postman/Swagger
5. Agregar rate limiting si es necesario
