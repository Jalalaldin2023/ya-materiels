from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class ClientIn(BaseModel):
    nom: str
    telephone: Optional[str] = None
    email: Optional[str] = None
    adresse: Optional[str] = None
    magasin_id: int


@router.get("")
def list_clients(magasin_id: int, search: str = ""):
    db = get_db()
    q = "SELECT * FROM clients WHERE magasin_id=?"
    params = [magasin_id]
    if search:
        q += " AND (nom LIKE ? OR telephone LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY nom"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{cid}")
def get_client(cid: int):
    db = get_db()
    row = db.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "Client non trouvé")
    ventes = db.execute("SELECT * FROM ventes WHERE client_id=? ORDER BY created_at DESC LIMIT 20", (cid,)).fetchall()
    db.close()
    return {**dict(row), "ventes": [dict(v) for v in ventes]}


@router.post("")
def create_client(c: ClientIn):
    db = get_db()
    cur = db.execute(
        "INSERT INTO clients (nom,telephone,email,adresse,magasin_id) VALUES (?,?,?,?,?)",
        (c.nom, c.telephone, c.email, c.adresse, c.magasin_id)
    )
    db.commit(); db.close()
    return {"id": cur.lastrowid, "message": "Client créé"}


@router.put("/{cid}")
def update_client(cid: int, c: ClientIn):
    db = get_db()
    db.execute("UPDATE clients SET nom=?,telephone=?,email=?,adresse=? WHERE id=?", (c.nom, c.telephone, c.email, c.adresse, cid))
    db.commit(); db.close()
    return {"message": "Client mis à jour"}


@router.delete("/{cid}")
def delete_client(cid: int):
    db = get_db()
    db.execute("DELETE FROM clients WHERE id=?", (cid,))
    db.commit(); db.close()
    return {"message": "Client supprimé"}
