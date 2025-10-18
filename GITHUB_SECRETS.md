# GitHub Secrets Configuration

## Secrets Requeridos

Configura estos secrets en GitHub antes del primer deploy:

**Repository**: `ProyectoIntegrdor2-LearnAI/search-api-lambda`

**Ruta**: `Settings → Secrets and variables → Actions → New repository secret`

---

### 1. ATLAS_URI

**Descripción**: MongoDB Atlas connection string

**Formato**:
```
mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/learnia_db?retryWrites=true&w=majority
```

**Cómo obtenerlo**:
1. MongoDB Atlas → Clusters → Connect
2. Choose connection method: "Connect your application"
3. Driver: Python, Version: 3.11 or later
4. Copy connection string
5. Reemplaza `<password>` con tu password real
6. Reemplaza `<dbname>` con `learnia_db`

**Ejemplo**:
```
mongodb+srv://learnia_user:MySecurePass123@learnia-cluster.abc123.mongodb.net/learnia_db?retryWrites=true&w=majority
```

---

### 2. POSTGRES_HOST

**Descripción**: RDS PostgreSQL endpoint

**Valor**:
```
learnia-postgres.criy8e4i62gn.us-east-2.rds.amazonaws.com
```

**Cómo verificarlo**:
```bash
aws rds describe-db-instances \
  --query 'DBInstances[?DBInstanceIdentifier==`learnia-postgres`].Endpoint.Address' \
  --output text
```

---

### 3. POSTGRES_PASSWORD

**Descripción**: PostgreSQL master password

**Formato**: String (contraseña que configuraste al crear el RDS)

**Nota**: Este es el password del usuario `postgres` en RDS

---

## Verificación

Después de configurar los secrets, verifica en:

```
Settings → Secrets and variables → Actions
```

Deberías ver:
- ✅ ATLAS_URI (Set X hours ago)
- ✅ POSTGRES_HOST (Set X hours ago)  
- ✅ POSTGRES_PASSWORD (Set X hours ago)

---

## Secrets Adicionales (Ya configurados en la organización)

Estos secrets deben estar configurados a nivel de organización o repositorio para que GitHub Actions funcione:

- `AWS_ROLE_ARN` o configuración OIDC para `aws-actions/configure-aws-credentials@v4`
- El workflow usa: `arn:aws:iam::974724840334:role/gh-actions-deploy-role`

---

## Testing

Después de configurar los secrets, haz un push a `main` para probar:

```bash
git add .
git commit -m "test: trigger deployment"
git push origin main
```

Ve a la pestaña `Actions` en GitHub para ver el progreso del deployment.

---

## Troubleshooting

### Error: "Secret ATLAS_URI not found"
- Verifica que el secret está escrito exactamente como `ATLAS_URI` (case-sensitive)
- Verifica que está en el repositorio correcto

### Error: "Connection refused" en MongoDB
- Verifica que el connection string incluye el password correcto
- Verifica que tu IP está en la whitelist de MongoDB Atlas (o usa `0.0.0.0/0` para permitir todo)

### Error: "Connection timed out" en PostgreSQL
- Verifica que el Security Group del RDS permite conexiones desde Lambda
- Verifica que Lambda está en la misma VPC que RDS (si aplica)

---

## Seguridad

- **NUNCA** commitees secrets en el código
- **NUNCA** hagas logs de los valores de los secrets
- Rota passwords regularmente
- Usa IAM roles en lugar de access keys cuando sea posible
