from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "backend_is_running", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return { "status":"ok"}