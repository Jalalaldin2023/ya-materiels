from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class AjustementIn(BaseModel):
    produit_id: int
    quantite: int
    type: str = "ajustement"
    notes: Optional[str] = None
    magasin_id: int


@router.get("/mouvements")
def list_mouvements(magasin_id: int, produit_id: int = 0, limit: int = 100):
    db = get_db()
    q = """SELECT m.*, p.nom as produit_nom, p.code as produit_code
           FROM mouvements_stock m JOIN produits p ON m.produit_id=p.id
           WHERE m.magasin_id=?"""
    params = [magasin_id]
    if produit_id:
        q += " AND m.produit_id=?"; params.append(produit_id)
    q += " ORDER BY m.created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/alertes")
def alertes_stock(magasin_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM produits WHERE magasin_id=? AND quantite<=quantite_min ORDER BY quantite ASC",
        (magasin_id,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("/ajustement")
def ajuster_stock(a: AjustementIn):
    db = get_db()
    try:
        if a.type == "entree":
            db.execute("UPDATE produits SET quantite=quantite+?,updated_at=datetime('now') WHERE id=?", (a.quantite, a.produit_id))
        elif a.type == "sortie":
            db.execute("UPDATE produits SET quantite=quantite-?,updated_at=datetime('now') WHERE id=?", (a.quantite, a.produit_id))
        else:
            db.execute("UPDATE produits SET quantite=?,updated_at=datetime('now') WHERE id=?", (a.quantite, a.produit_id))
        db.execute(
            "INSERT INTO mouvements_stock (produit_id,type,quantite,notes,magasin_id) VALUES (?,?,?,?,?)",
            (a.produit_id, a.type, a.quantite, a.notes, a.magasin_id)
        )
        db.commit()
        return {"message": "Stock ajusté"}
    finally:
        db.close()
