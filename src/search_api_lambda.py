import json
import logging
import os
import re
from typing import Any, Dict, Optional

from utils.bedrock_client import get_bedrock_client
from utils.mongodb_client import get_mongo_client
from utils.postgres_client import get_favorites_repository

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": os.getenv("CORS_ALLOW_ORIGIN", "*"),
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
}


class SearchApiError(Exception):
    """Errores controlados del servicio."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    logger.debug("Incoming event: %s", json.dumps(event))

    method = _get_http_method(event)
    path = _get_path(event)

    if method == "OPTIONS":
        return _build_response(200, {})

    try:
        if method == "POST" and path == "/api/search":
            payload = _parse_json_body(event)
            return _build_response(200, _handle_search(payload))

        if method == "GET" and path == "/api/courses/categories":
            return _build_response(200, _handle_get_categories())

        if method == "GET" and path == "/api/courses/trending":
            limit = _get_query_param(event, "limit", default=12)
            return _build_response(200, _handle_get_trending(limit))

        course_match = re.match(r"^/api/courses/(?P<course_id>[^/]+)$", path)
        if method == "GET" and course_match:
            course_id = course_match.group("course_id")
            return _build_response(200, _handle_get_course(course_id))

        favorite_match = re.match(r"^/api/courses/(?P<course_id>[^/]+)/favorite$", path)
        if method == "POST" and favorite_match:
            user_id = _extract_user_id(event)
            if not user_id:
                raise SearchApiError("No se encontró el usuario autenticado", 401)
            course_id = favorite_match.group("course_id")
            payload = _parse_json_body(event, default={})
            return _build_response(200, _handle_toggle_favorite(user_id, course_id, payload))

        raise SearchApiError(f"Ruta no encontrada: {method} {path}", 404)

    except SearchApiError as exc:
        logger.warning("Error controlado: %s", exc.message)
        return _build_response(exc.status_code, {"error": exc.message})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado procesando la petición")
        return _build_response(500, {"error": "Error interno del servidor"})


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


def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def _parse_json_body(event: Dict[str, Any], default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if "body" not in event or event["body"] in (None, ""):
        return default or {}

    body = event["body"]
    if event.get("isBase64Encoded"):
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


# Evitar import circular en _parse_json_body
try:  # pragma: no cover - base64 solo se usa con API Gateway
    import base64
except ImportError:  # pragma: no cover
    base64 = None
