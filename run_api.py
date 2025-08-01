import uvicorn

# from src.api.app import app

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
