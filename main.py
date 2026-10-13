from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

# Import the tracing module first so .env (Langfuse keys) is loaded early.
from config.langfuse_tracing import TRACING_ENABLED, shutdown_tracing, trace_http_request
from routers.movies import movie_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Flush any buffered Langfuse traces before the process exits.
    shutdown_tracing()


app = FastAPI(title = "Movie Booking API", lifespan=lifespan)

if TRACING_ENABLED:
    # One Langfuse trace per HTTP request.
    @app.middleware("http")
    async def langfuse_tracing_middleware(request: Request, call_next):
        return await trace_http_request(request, call_next)

app.include_router(movie_app)
