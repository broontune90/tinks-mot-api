from fastapi import FastAPI

app = FastAPI(title="Tinks Vehicle Check API")


@app.get("/")
def home():
    return {
        "app": "Tinks Vehicle Check",
        "status": "online"
    }


@app.get("/health")
def health():
    return {"status": "ok"}
