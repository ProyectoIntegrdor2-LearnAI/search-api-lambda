<<<<<<< HEAD
# search-api-lambda
=======
Search API Lambda
=================

Esta función Lambda expone un servicio de búsqueda semántica de cursos para la
plataforma **LearnIA**. Permite a los clientes realizar búsquedas por texto,
consultar cursos populares o por categorías y gestionar la lista de favoritos
de cada usuario.
# Search API Lambda

Esta función Lambda expone un servicio de búsqueda semántica de cursos
para la plataforma LearnIA. Permite a los clientes realizar búsquedas por
texto, consultar cursos populares o por categorías y gestionar la lista
de favoritos de cada usuario.

Endpoints
---------

La Lambda se despliega detrás de un API Gateway HTTP y expone los
siguientes endpoints:

| Método | Ruta                            | Descripción                                |
|--------|---------------------------------|--------------------------------------------|
| POST   | /api/search                     | Búsqueda semántica principal               |
| GET    | /api/courses/{id}               | Detalle de un curso por ID                 |
| GET    | /api/courses/categories         | Lista de categorías disponibles            |
| GET    | /api/courses/trending           | Cursos populares (orden configurable)      |
| POST   | /api/courses/{id}/favorite      | Añadir/Quitar curso de favoritos          |

Arquitectura
------------

* MongoDB Atlas – almacena el catálogo de cursos y sus vectores de
  embedding.
* AWS Bedrock – Titan Text Embeddings – genera embeddings para las
  consultas del motor semántico.
* PostgreSQL – guarda la relación usuario ↔ curso favorito.
* AWS CloudWatch – logs y métricas básicas.

Variables de entorno principales
--------------------------------

```
ATLAS_URI=<cadena de conexión MongoDB SRV>
ATLAS_SEARCH_INDEX=default
DATABASE_NAME=learnia_db
COLLECTION_NAME=courses

EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
EMBEDDING_DIM=1024

POSTGRES_HOST=...
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_PORT=5432

FAVORITES_TABLE=user_course_favorites
FAVORITES_PARTITION_KEY=user_id
```

Despliegue con AWS SAM
----------------------

```
sam build --use-container
sam deploy --guided
```

La plantilla `template.yaml` configura un `AWS::Serverless::Function`
con un API Gateway HTTP y rutas bajo `/api/*`. El handler principal se
encuentra en `src/search_api_lambda.lambda_handler`.

Desarrollo local
----------------

1. Crear un virtualenv y instalar dependencias:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r src/requirements.txt
   ```
2. Exportar las variables de entorno indicadas arriba.
3. Ejecutar pruebas unitarias (pendiente de implementar) o invocar
   manualmente `search_api_lambda.lambda_handler` desde una consola de
   Python.

Integración con el frontend
---------------------------

El frontend (`pi2-frontend/src/services/apiServices.js`) ya prepara
llamadas a estos endpoints bajo el namespace `COURSES`. Solo es
necesario apuntar `REACT_APP_COURSES_LAMBDA_URL` (o la variable
equivalente en la configuración de despliegue) a la URL del API
Gateway generado por esta Lambda.
