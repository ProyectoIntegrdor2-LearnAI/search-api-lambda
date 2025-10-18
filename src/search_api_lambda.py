import json
import logging
import os
import re
from typing import Any, Dict, Optional, List

from utils.bedrock_client import get_bedrock_client
from utils.mongodb_client import get_mongo_client
from utils.postgres_client import get_favorites_repository

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)


class SearchApiError(Exception):
    """Errores controlados del servicio."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_allowed_origins() -> List[str]:
    """Obtiene los orígenes permitidos desde variables de entorno."""
    cors_origin = os.getenv("CORS_ORIGIN", "")
    if not cors_origin:
        return ["*"]
    
    origins = [origin.strip() for origin in cors_origin.split(",")]
    return [origin for origin in origins if origin]


def _normalize_origin(origin: str) -> str:
    """Normaliza un origen para comparación."""
    if not origin or origin == "*":
        return origin
    
    # Eliminar espacios y asegurar que tenga esquema
    sanitized = origin.strip().replace(" ", "")
    
    if not sanitized.startswith(("http://", "https://")):
        sanitized = f"https://{sanitized.lstrip('/')}"
    
    # Normalizar a minúsculas y eliminar trailing slash
    try:
        from urllib.parse import urlparse
        parsed = urlparse(sanitized)
        normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if parsed.port and parsed.hostname:
            normalized = f"{parsed.scheme.lower()}://{parsed.hostname.lower()}:{parsed.port}"
        return normalized
    except Exception:
        return sanitized.rstrip("/").lower()


def _is_origin_allowed(origin: Optional[str], allowed_origins: List[str]) -> bool:
    """Verifica si un origen está permitido."""
    if not origin:
        return True  # Requests sin origin header son permitidos (ej: curl)
    
    if "*" in allowed_origins:
        return True
    
    normalized_origin = _normalize_origin(origin)
    normalized_allowed = [_normalize_origin(o) for o in allowed_origins]
    
    return normalized_origin in normalized_allowed


def _build_cors_headers(request_origin: Optional[str]) -> Dict[str, str]:
    """Construye los headers CORS dinámicamente basado en el origen de la petición."""
    allowed_origins = _get_allowed_origins()
    
    # Si no hay origen en la petición y no permitimos todo
    if not request_origin and "*" not in allowed_origins and allowed_origins:
        request_origin = allowed_origins[0]
    
    # Verificar si el origen está permitido
    if request_origin and not _is_origin_allowed(request_origin, allowed_origins):
        # Si el origen no está permitido, usar el primer origen permitido
        request_origin = allowed_origins[0] if allowed_origins and "*" not in allowed_origins else "*"
    
    # Determinar el valor del header Allow-Origin
    if "*" in allowed_origins:
        allow_origin = "*"
    elif request_origin:
        allow_origin = _normalize_origin(request_origin)
    elif allowed_origins:
        allow_origin = allowed_origins[0]
    else:
        allow_origin = "*"
    
    # Construir headers
    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With,Accept,Origin,user-id,x-user-id",
        "Access-Control-Allow-Credentials": "false" if allow_origin == "*" else "true",
    }
    
    # Agregar Vary header si no es wildcard
    if allow_origin != "*":
        headers["Vary"] = "Origin"
    
    return headers


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    logger.debug("Incoming event: %s", json.dumps(event))

    # Obtener el origen de la petición
    headers = event.get("headers") or {}
    request_origin = headers.get("origin") or headers.get("Origin")
    
    # Construir headers CORS dinámicamente
    cors_headers = _build_cors_headers(request_origin)

    method = _get_http_method(event)
    path = _get_path(event)

    # Manejar preflight OPTIONS
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": cors_headers,
            "body": ""
        }

    try:
        if method == "POST" and path == "/api/search":
            payload = _parse_json_body(event)
            return _build_response(200, _handle_search(payload), cors_headers)

        if method == "GET" and path == "/api/courses/categories":
            return _build_response(200, _handle_get_categories(), cors_headers)

        if method == "GET" and path == "/api/courses/trending":
            limit = _get_query_param(event, "limit", default=12)
            return _build_response(200, _handle_get_trending(limit), cors_headers)

        course_match = re.match(r"^/api/courses/(?P<course_id>[^/]+)$", path)
        if method == "GET" and course_match:
            course_id = course_match.group("course_id")
            return _build_response(200, _handle_get_course(course_id), cors_headers)

        favorite_match = re.match(r"^/api/courses/(?P<course_id>[^/]+)/favorite$", path)
        if method == "POST" and favorite_match:
            user_id = _extract_user_id(event)
            if not user_id:
                raise SearchApiError("No se encontró el usuario autenticado", 401)
            course_id = favorite_match.group("course_id")
            payload = _parse_json_body(event, default={})
            return _build_response(200, _handle_toggle_favorite(user_id, course_id, payload), cors_headers)

        raise SearchApiError(f"Ruta no encontrada: {method} {path}", 404)

    except SearchApiError as exc:
        logger.warning("Error controlado: %s", exc.message)
        return _build_response(exc.status_code, {"error": exc.message}, cors_headers)
    except Exception as exc:
        logger.exception("Error inesperado procesando la petición")
        return _build_response(500, {"error": "Error interno del servidor"}, cors_headers)


def _handle_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = (payload.get("query") or "").strip()
    if len(query) < 3:
        raise SearchApiError("El parámetro 'query' debe tener al menos 3 caracteres", 400)

    limit = int(payload.get("limit") or 12)
    limit = max(1, min(limit, 40))

    filters = payload.get("filters") or {}

    bedrock = get_bedrock_client()
    mongo = get_mongo_client()

    embedding = bedrock.generate_embedding(query)
    courses = mongo.search_courses(embedding, limit=limit, filters=filters)

    return {
        "results": courses,
        "total": len(courses),
        "query": query,
    }


def _handle_get_course(course_id: str) -> Dict[str, Any]:
    mongo = get_mongo_client()
    course = mongo.get_course_by_id(course_id)
    if not course:
        raise SearchApiError("Curso no encontrado", 404)
    return {"course": course}


def _handle_get_categories() -> Dict[str, Any]:
    mongo = get_mongo_client()
    categories = mongo.get_categories()
    return {"categories": categories}


def _handle_get_trending(limit: int) -> Dict[str, Any]:
    mongo = get_mongo_client()
    courses = mongo.get_trending_courses(limit=limit)
    return {"courses": courses, "total": len(courses)}


def _handle_toggle_favorite(user_id: str, course_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    action = (payload.get("action") or "").lower()
    favorites_repo = get_favorites_repository()

    if action not in {"", "add", "remove"}:
        raise SearchApiError("El parámetro 'action' debe ser add, remove o omitirse", 400)

    if action == "add":
        is_favorite = favorites_repo.set_favorite(user_id, course_id, should_favorite=True)
    elif action == "remove":
        is_favorite = favorites_repo.set_favorite(user_id, course_id, should_favorite=False)
    else:
        is_current_favorite = favorites_repo.is_favorite(user_id, course_id)
        is_favorite = favorites_repo.set_favorite(user_id, course_id, should_favorite=not is_current_favorite)

    return {
        "course_id": course_id,
        "is_favorite": is_favorite,
    }


def _build_response(status_code: int, body: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": cors_headers,
        "body": json.dumps(body, ensure_ascii=False),
    }


def _parse_json_body(event: Dict[str, Any], default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if "body" not in event or event["body"] in (None, ""):
        return default or {}

    body = event["body"]
    if event.get("isBase64Encoded"):
        if base64 is None:
            raise SearchApiError("Base64 decoding no está disponible", 500)
        body = body.encode("utf-8")
        body = base64.b64decode(body).decode("utf-8")

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SearchApiError("El cuerpo debe ser JSON válido", 400) from exc


def _get_http_method(event: Dict[str, Any]) -> str:
    return (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    ).upper()


def _get_path(event: Dict[str, Any]) -> str:
    path = event.get("rawPath") or event.get("path") or ""
    return path.rstrip("/") if path != "/" else path


def _get_query_param(event: Dict[str, Any], name: str, default: Optional[int] = None) -> int:
    params = event.get("queryStringParameters") or {}
    value = params.get(name)
    if value is None:
        return int(default) if default is not None else 0
    try:
        return int(value)
    except ValueError as exc:
        raise SearchApiError(f"El parámetro '{name}' debe ser numérico", 400) from exc


def _extract_user_id(event: Dict[str, Any]) -> Optional[str]:
    try:
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    except KeyError:
        pass

    headers = event.get("headers") or {}
    return headers.get("user-id") or headers.get("x-user-id")


try:
    import base64
except ImportError:
    base64 = None