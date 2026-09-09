from fastapi import FastAPI

app = FastAPI("Capstone")

@app.get("/health")
def health():
    return {"status": "ok"} 