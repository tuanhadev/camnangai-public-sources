from fastapi import FastAPI

app = FastAPI(title="Demo API")


@app.get("/")
def root():
    return {"message": "ok"}
