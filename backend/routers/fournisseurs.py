from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class FournisseurIn(BaseModel):
    nom: str
    telephone: Optional[str] = None
    email: Optional[str] = None
    adresse: Optional[str] = None
    magasin_id: int


@router.get("")
def list_fournisseurs(magasin_id: int, search: str = ""):
    db = get_db()
    q = "SELECT * FROM fournisseurs WHERE magasin_id=?"
    params = [magasin_id]
    if search:
        q += " AND nom LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY nom"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("")
def create_fournisseur(f: FournisseurIn):
    db = get_db()
    cur = db.execute(
        "INSERT INTO fournisseurs (nom,telephone,email,adresse,magasin_id) VALUES (?,?,?,?,?)",
        (f.nom, f.telephone, f.email, f.adresse, f.magasin_id)
    )
    db.commit(); db.close()
    return {"id": cur.lastrowid, "message": "Fournisseur créé"}


@router.put("/{fid}")
def update_fournisseur(fid: int, f: FournisseurIn):
    db = get_db()
    db.execute("UPDATE fournisseurs SET nom=?,telephone=?,email=?,adresse=? WHERE id=?", (f.nom, f.telephone, f.email, f.adresse, fid))
    db.commit(); db.close()
    return {"message": "Fournisseur mis à jour"}


@router.delete("/{fid}")
def delete_fournisseur(fid: int):
    db = get_db()
    db.execute("DELETE FROM fournisseurs WHERE id=?", (fid,))
    db.commit(); db.close()
    return {"message": "Fournisseur supprimé"}
