from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import traceback

from database import init_db
from routers import produits, ventes, clients, fournisseurs, achats, depenses, stock, dashboard, auth

app = FastAPI(title="Quincaillerie API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})

app.include_router(produits.router, prefix="/api/produits", tags=["Produits"])
app.include_router(ventes.router, prefix="/api/ventes", tags=["Ventes"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(fournisseurs.router, prefix="/api/fournisseurs", tags=["Fournisseurs"])
app.include_router(achats.router, prefix="/api/achats", tags=["Achats"])
app.include_router(depenses.router, prefix="/api/depenses", tags=["Dépenses"])
app.include_router(stock.router, prefix="/api/stock", tags=["Stock"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# Serve frontend — cherche d'abord static/ (Render), puis ../frontend/ (dev local)
for _fp in [
    os.path.join(os.path.dirname(__file__), "static"),
    os.path.join(os.path.dirname(__file__), "..", "frontend"),
]:
    if os.path.exists(_fp):
        app.mount("/", StaticFiles(directory=_fp, html=True), name="frontend")
        break


@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
