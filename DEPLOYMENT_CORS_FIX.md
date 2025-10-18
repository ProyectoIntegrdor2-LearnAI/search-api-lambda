# Fix de CORS para Search API Lambda

## Problema Identificado

El API Gateway HttpApi estaba devolviendo 404 en peticiones OPTIONS porque:

1. El stage estaba configurado como `Prod`, pero las peticiones se hacían sin el prefijo `/Prod/`
2. La configuración CORS de HttpApi necesita que el stage sea `$default` para rutas sin prefijo

## Cambios Realizados

### 1. Template.yaml

- Cambiado `StageName: Prod` a `StageName: $default`
- Simplificada la configuración de eventos (un solo evento proxy `/{proxy+}`)
- Ajustada variable de entorno de `CORS_ALLOW_ORIGIN` a `CORS_ORIGIN`
- Agregados más headers permitidos en CORS

### 2. Configuración CORS

La configuración final de CORS en el template:

```yaml
CorsConfiguration:
  AllowOrigins:
    - !Ref CorsAllowOrigin
  AllowMethods:
    - GET
    - POST
    - PUT
    - DELETE
    - OPTIONS
  AllowHeaders:
    - Content-Type
    - Authorization
    - X-User-Id
    - x-user-id
    - user-id
    - Origin
    - Accept
    - X-Requested-With
  MaxAge: 600
  AllowCredentials: false
```

## Despliegue

### Opción 1: Via GitHub Actions (Recomendado)

El workflow ya está configurado. Solo necesitas:

```bash
git add .
git commit -m "fix: update CORS configuration and stage name"
git push origin main
```

### Opción 2: Despliegue Manual con SAM

```bash
cd /home/raul/Documents/Proyecto_Integrador_2/Repositorios/search-api-lambda

# Build
sam build

# Deploy (actualizará el stack existente)
sam deploy \
  --stack-name learnia-search-api \
  --parameter-overrides \
    Environment=prod \
    CorsAllowOrigin=https://www.learn-ia.app \
    AtlasUri="tu-atlas-uri" \
    PostgresHost="tu-rds-host" \
    PostgresPassword="tu-password" \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset
```

## Verificación

### 1. Test de Preflight (OPTIONS)

```bash
curl -X OPTIONS https://463dscc3hl.execute-api.us-east-2.amazonaws.com/api/courses/trending \
  -H "Origin: https://www.learn-ia.app" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

Respuesta esperada:
- Status: 200 o 204
- Headers incluyen:
  - `Access-Control-Allow-Origin: https://www.learn-ia.app`
  - `Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS`
  - `Access-Control-Allow-Headers: ...`

### 2. Test de GET Request

```bash
curl -X GET https://463dscc3hl.execute-api.us-east-2.amazonaws.com/api/courses/trending \
  -H "Origin: https://www.learn-ia.app" \
  -v
```

Respuesta esperada:
- Status: 200
- Body: JSON con cursos trending
- Headers CORS presentes

### 3. Test desde Frontend

Una vez desplegado, el frontend debería poder hacer peticiones sin errores CORS:

```javascript
// En el navegador (desde https://www.learn-ia.app)
fetch('https://463dscc3hl.execute-api.us-east-2.amazonaws.com/api/courses/trending', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));
```

## Comportamiento Esperado de HttpApi

Con `$default` stage:
- Las rutas se acceden directamente sin prefijo: `/api/courses/trending`
- API Gateway maneja automáticamente OPTIONS cuando `CorsConfiguration` está presente
- La Lambda solo recibe peticiones no-OPTIONS (GET, POST, etc.)

## Troubleshooting

### Si sigues viendo 404:

1. Verifica que el API Gateway esté correctamente actualizado:
   ```bash
   aws apigatewayv2 get-apis --region us-east-2 | grep 463dscc3hl
   ```

2. Verifica las rutas configuradas:
   ```bash
   aws apigatewayv2 get-routes --api-id 463dscc3hl --region us-east-2
   ```

3. Verifica la configuración CORS:
   ```bash
   aws apigatewayv2 get-api --api-id 463dscc3hl --region us-east-2
   ```

### Si ves errores CORS pero 200 OK:

Verifica que los headers de la Lambda estén correctos. La Lambda ya está configurada para:
- Leer el origen de la petición
- Validarlo contra `CORS_ORIGIN`
- Devolver headers CORS apropiados

### Si el despliegue falla:

1. Verifica que todos los parámetros estén en GitHub Secrets
2. Verifica que el rol de GitHub Actions tenga permisos
3. Revisa los logs de CloudFormation en la consola de AWS

## URLs Relevantes

- API Gateway: https://463dscc3hl.execute-api.us-east-2.amazonaws.com
- Frontend: https://www.learn-ia.app
- Console AWS (API Gateway): https://console.aws.amazon.com/apigateway/home?region=us-east-2

## Notas Importantes

- El `$default` stage es específico de HttpApi (API Gateway v2)
- Si necesitas múltiples stages (dev, prod), considera usar REST API (Api) en lugar de HttpApi
- HttpApi es más simple y barato, pero tiene menos features que REST API
