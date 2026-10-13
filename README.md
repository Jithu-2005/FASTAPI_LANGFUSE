# movie-booking-api-jithendra-1

FastAPI + SQLAlchemy movie booking API, instrumented with [Langfuse](https://langfuse.com/docs) tracing.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in DATABASE_URL and the Langfuse keys
uvicorn main:app --reload
```

## Langfuse tracing

Every HTTP request becomes one Langfuse trace with nested spans:

```
POST /bookings                          <- root span (middleware in main.py)
└── Servicelayer.book_tickets           <- business logic (metadata: total_amount, seats...)
    └── BookingRepository.add_booking   <- data access
```

* Setup: create a project at https://cloud.langfuse.com, copy the API keys into `.env`.
* Code: `config/langfuse_tracing.py` (middleware, `@traced()` decorator, `annotate()`).
* Optional request headers: `X-User-Id` (Langfuse user) and `X-Session-Id` (Langfuse session).
* Each response has an `X-Trace-Id` header - search for it in Langfuse to open that exact trace.
* No keys / package missing / `LANGFUSE_TRACING_ENABLED=false` -> tracing is skipped and the API works as before.
* Request bodies are not recorded by the middleware; DB sessions are never recorded.
