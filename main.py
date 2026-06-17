from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.routes import auth, assignment

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect Routers to Gateway Pipeline
app.include_router(auth.router, prefix="/api/v1")
app.include_router(assignment.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "healthy", "app": settings.APP_NAME}
