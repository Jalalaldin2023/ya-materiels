from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class DepenseIn(BaseModel):
    description: str
    montant: float
    categorie: str = "autre"
    date: Optional[str] = None
    notes: Optional[str] = None
    magasin_id: int


@router.get("")
def list_depenses(magasin_id: int, date_debut: str = "", date_fin: str = ""):
    db = get_db()
    q = "SELECT * FROM depenses WHERE magasin_id=?"
    params = [magasin_id]
    if date_debut:
        q += " AND date>=?"; params.append(date_debut)
    if date_fin:
        q += " AND date<=?"; params.append(date_fin)
    q += " ORDER BY date DESC, created_at DESC"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("")
def create_depense(d: DepenseIn):
    db = get_db()
    cur = db.execute(
        "INSERT INTO depenses (description,montant,categorie,date,notes,magasin_id) VALUES (?,?,?,?,?,?)",
        (d.description, d.montant, d.categorie, d.date, d.notes, d.magasin_id)
    )
    db.commit(); db.close()
    return {"id": cur.lastrowid, "message": "Dépense enregistrée"}


@router.delete("/{did}")
def delete_depense(did: int):
    db = get_db()
    db.execute("DELETE FROM depenses WHERE id=?", (did,))
    db.commit(); db.close()
    return {"message": "Dépense supprimée"}
