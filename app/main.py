import time
print("Iniciando aplicación...")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

print("Imports completados")

from app.database import engine, Base
from app.api.v1 import v1_router  

# Crear tablas con timeout/debug
try:
    print("Inicializando base de datos...")
    start = time.time()
    Base.metadata.create_all(bind=engine)
    print(f"BD lista en {time.time() - start:.2f}s")
except Exception as e:
    print(f"Error BD: {e}")


app = FastAPI(title="Thesis Platform API")

print("Configurando middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Incluyendo routers...")
app.include_router(v1_router, prefix="/api/v1")

@app.get("/")
def root():
    print("Alguien accedió a /")
    return {"message": "Thesis Platform API", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

print("Aplicación lista")

# FIX: Handlers de excepciones con tipos correctos
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno: {str(exc)}"},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )