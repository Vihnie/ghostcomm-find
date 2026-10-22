from fastapi import FastAPI

app = FastAPI(
    title="GhostComm",
    description="Secure AI-powered lost and found platform.",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "GhostComm Find API is running!",
        "status": "online"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
