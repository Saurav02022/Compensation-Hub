from fastapi import FastAPI

app = FastAPI(title="Compensation Hub API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "compensation-hub-api"}
