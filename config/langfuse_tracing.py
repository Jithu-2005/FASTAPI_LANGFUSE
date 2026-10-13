"""
Langfuse tracing for the Movie Booking API.

What you get in Langfuse for every HTTP request:

    POST /bookings                         <- root span (created by the middleware)
    └── Servicelayer.book_tickets          <- business-logic span
        └── BookingRepository.add_booking  <- data-access span

Design goals
------------
* Tracing must NEVER break the API. If the langfuse package is missing, the
  API keys are not set, or LANGFUSE_TRACING_ENABLED=false, every helper in this
  file silently becomes a no-op and the app behaves exactly as before.
* Never put a SQLAlchemy Session or ORM object into a trace. Inputs/outputs are
  converted to plain, size-limited JSON first (see `_to_plain`).
* Request bodies are not captured by the middleware. The service-layer spans
  already record the validated pydantic inputs.

Configuration (.env)
--------------------
    LANGFUSE_PUBLIC_KEY=pk-lf-...
    LANGFUSE_SECRET_KEY=sk-lf-...
    LANGFUSE_BASE_URL=https://cloud.langfuse.com     # or your self-hosted URL
    LANGFUSE_TRACING_ENVIRONMENT=development         # optional
    LANGFUSE_TRACING_ENABLED=true                    # optional kill switch
"""

import functools
import inspect
import logging
import os
from typing import Any, Callable, Optional

from dotenv import load_dotenv

# Must run before we read any LANGFUSE_* variable below.
load_dotenv()

logger = logging.getLogger("movie_booking.tracing")

try:
    from langfuse import get_client, observe, propagate_attributes

    _SDK_INSTALLED = True
except ImportError:  # langfuse not installed -> run without tracing
    _SDK_INSTALLED = False


def _is_enabled() -> bool:
    if not _SDK_INSTALLED:
        logger.warning("Langfuse tracing OFF: 'langfuse' package is not installed.")
        return False
    if os.getenv("LANGFUSE_TRACING_ENABLED", "true").strip().lower() in ("0", "false", "no", "off"):
        logger.info("Langfuse tracing OFF: LANGFUSE_TRACING_ENABLED is false.")
        return False
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        logger.warning(
            "Langfuse tracing OFF: set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env."
        )
        return False
    logger.info("Langfuse tracing ON.")
    return True


TRACING_ENABLED: bool = _is_enabled()

# Paths that would only add noise to the trace list.
IGNORED_PATHS = {"/docs", "/redoc", "/openapi.json", "/favicon.ico"}

_MAX_STR = 500
_MAX_ITEMS = 20
_MAX_DEPTH = 4


# --------------------------------------------------------------------------- #
# Safe serialisation helpers
# --------------------------------------------------------------------------- #
def _truncate(text: str) -> str:
    return text if len(text) <= _MAX_STR else text[:_MAX_STR] + "…"


def _to_plain(value: Any, depth: int = 0) -> Any:
    """Convert pydantic models / ORM rows / containers into small JSON-safe data."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate(value)
    if depth >= _MAX_DEPTH:
        return _truncate(repr(value))

    # pydantic v2 model
    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump(), depth + 1)
        except Exception:
            return _truncate(repr(value))

    # SQLAlchemy ORM instance: read only what is already loaded (vars() never
    # triggers a lazy-load / refresh query), skip SQLAlchemy internals.
    if hasattr(value, "__table__"):
        return {k: _to_plain(v, depth + 1) for k, v in vars(value).items() if not k.startswith("_")}

    if isinstance(value, dict):
        return {str(k): _to_plain(v, depth + 1) for k, v in list(value.items())[:_MAX_ITEMS]}

    if isinstance(value, (list, tuple, set)):
        items = list(value)
        out = [_to_plain(v, depth + 1) for v in items[:_MAX_ITEMS]]
        if len(items) > _MAX_ITEMS:
            out.append(f"... {len(items) - _MAX_ITEMS} more")
        return out

    return _truncate(repr(value))


def _looks_like_db_session(value: Any) -> bool:
    return hasattr(value, "commit") and hasattr(value, "query")


def _describe_call(func: Callable, args: tuple, kwargs: dict) -> Optional[dict]:
    """Build a readable {param: value} dict, leaving out self/cls and DB sessions."""
    try:
        bound = inspect.signature(func).bind(*args, **kwargs)
    except TypeError:
        return None
    return {
        name: _to_plain(val)
        for name, val in bound.arguments.items()
        if name not in ("self", "cls") and not _looks_like_db_session(val)
    }


def _update_span(**kwargs: Any) -> None:
    """Update the currently active span; never raise."""
    try:
        get_client().update_current_span(**kwargs)
    except Exception:
        logger.debug("Langfuse span update failed", exc_info=True)


# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #
def traced(name: Optional[str] = None, as_type: str = "span") -> Callable:
    """
    Decorator: wrap a function in a Langfuse observation.

    Records sanitised inputs, outputs, duration and any exception.
    Works for sync and async functions. No-op when tracing is disabled.

        @traced()                        # span named "Class.method"
        @traced("custom-name")
        @traced("answer", as_type="generation")   # for a future LLM call
    """

    def decorator(func: Callable) -> Callable:
        if not TRACING_ENABLED:
            return func

        span_name = name or func.__qualname__

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                _update_span(input=_describe_call(func, args, kwargs))
                result = await func(*args, **kwargs)
                _update_span(output=_to_plain(result))
                return result

            wrapper: Callable = async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                _update_span(input=_describe_call(func, args, kwargs))
                result = func(*args, **kwargs)
                _update_span(output=_to_plain(result))
                return result

            wrapper = sync_wrapper

        # We record input/output ourselves (sanitised), so turn the SDK's
        # automatic capture off to avoid serialising Sessions / ORM objects.
        return observe(
            name=span_name,
            as_type=as_type,
            capture_input=False,
            capture_output=False,
        )(wrapper)

    return decorator


def annotate(**metadata: Any) -> None:
    """Attach business metadata (e.g. total_amount) to the current span."""
    if TRACING_ENABLED:
        _update_span(metadata=_to_plain(metadata))


def _route_template(request: Any) -> str:
    """'/movies/42' -> '/movies/{movie_id}' so trace names stay low-cardinality."""
    try:
        from starlette.routing import Match

        for route in request.app.router.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path
    except Exception:
        pass
    return request.url.path


async def trace_http_request(request: Any, call_next: Callable) -> Any:
    """
    HTTP middleware body: one root span (= one Langfuse trace) per request.

    Optional request headers that enrich the trace:
        X-User-Id     -> Langfuse "user"    (cost/usage per user, user view)
        X-Session-Id  -> Langfuse "session" (group several calls together)
    The response gets an `X-Trace-Id` header so you can paste it into Langfuse.
    """
    if not TRACING_ENABLED or request.url.path in IGNORED_PATHS:
        return await call_next(request)

    client = get_client()
    route = _route_template(request)
    trace_name = f"{request.method} {route}"

    # propagate_attributes: values must be strings <= 200 chars,
    # metadata keys must be alphanumeric.
    attributes: dict = {
        "trace_name": trace_name,
        "tags": ["movie-booking", "fastapi"],
        "metadata": {"method": request.method, "route": route[:200]},
    }
    if request.headers.get("x-user-id"):
        attributes["user_id"] = request.headers["x-user-id"][:200]
    if request.headers.get("x-session-id"):
        attributes["session_id"] = request.headers["x-session-id"][:200]

    with client.start_as_current_observation(
        as_type="span",
        name=trace_name,
        input={
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
        },
    ) as root_span:
        with propagate_attributes(**attributes):
            try:
                response = await call_next(request)
            except Exception as exc:
                root_span.update(level="ERROR", status_message=_truncate(str(exc)))
                raise

            level = "ERROR" if response.status_code >= 500 else (
                "WARNING" if response.status_code >= 400 else "DEFAULT"
            )
            root_span.update(
                output={"status_code": response.status_code},
                level=level,
                status_message=f"HTTP {response.status_code}",
            )
            try:
                response.headers["X-Trace-Id"] = client.get_current_trace_id() or ""
            except Exception:
                pass
            return response


def shutdown_tracing() -> None:
    """Flush buffered traces on app shutdown so the last requests aren't lost."""
    if not TRACING_ENABLED:
        return
    try:
        get_client().shutdown()
    except Exception:
        logger.debug("Langfuse shutdown failed", exc_info=True)
