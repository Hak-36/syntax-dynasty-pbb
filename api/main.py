from fastapi import FastAPI

app = FastAPI(title="Pre-Meeting Briefing Agent")


@app.get("/health")
def health():
    return {"status": "ok"}