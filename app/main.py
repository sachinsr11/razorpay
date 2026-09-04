"""FastAPI application entrypoint for Reclaim."""

from fastapi import FastAPI

app = FastAPI(title="Reclaim", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the API process is available."""

    return {"status": "ok"}
