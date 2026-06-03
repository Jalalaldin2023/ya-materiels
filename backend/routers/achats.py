from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter()


class LigneAchatIn(BaseModel):
    produit_id: int
    quantite: int
    prix_unitaire: float


class AchatIn(BaseModel):
    magasin_id: int
    fournisseur_id: Optional[int] = None
    lignes: List[LigneAchatIn]
    montant_paye: float = 0
    statut: str = "paye"
    notes: Optional[str] = None


def gen_numero(magasin_id, db):
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"AC{magasin_id}-{today}"
    count = db.execute("SELECT COUNT(*) FROM achats WHERE numero LIKE ?", (f"{prefix}%",)).fetchone()[0]
    return f"{prefix}-{count+1:03d}"


@router.get("")
def list_achats(magasin_id: int, search: str = ""):
    db = get_db()
    q = """SELECT a.*, f.nom as fournisseur_nom FROM achats a
           LEFT JOIN fournisseurs f ON a.fournisseur_id=f.id WHERE a.magasin_id=?"""
    params = [magasin_id]
    if search:
        q += " AND (a.numero LIKE ? OR f.nom LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY a.created_at DESC"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{aid}")
def get_achat(aid: int):
    db = get_db()
    achat = db.execute(
        "SELECT a.*, f.nom as fournisseur_nom FROM achats a LEFT JOIN fournisseurs f ON a.fournisseur_id=f.id WHERE a.id=?",
        (aid,)
    ).fetchone()
    if not achat:
        raise HTTPException(404, "Achat non trouvé")
    lignes = db.execute(
        "SELECT al.*, p.nom as produit_nom FROM achat_lignes al JOIN produits p ON al.produit_id=p.id WHERE al.achat_id=?",
        (aid,)
    ).fetchall()
    db.close()
    return {**dict(achat), "lignes": [dict(l) for l in lignes]}


@router.post("")
def create_achat(a: AchatIn):
    db = get_db()
    try:
        total = sum(l.quantite * l.prix_unitaire for l in a.lignes)
        numero = gen_numero(a.magasin_id, db)
        statut = a.statut if a.montant_paye >= total else "credit"

        cur = db.execute(
            "INSERT INTO achats (numero,fournisseur_id,total,montant_paye,statut,notes,magasin_id) VALUES (?,?,?,?,?,?,?)",
            (numero, a.fournisseur_id, total, a.montant_paye, statut, a.notes, a.magasin_id)
        )
        achat_id = cur.lastrowid

        for ligne in a.lignes:
            ltotal = ligne.quantite * ligne.prix_unitaire
            db.execute(
                "INSERT INTO achat_lignes (achat_id,produit_id,quantite,prix_unitaire,total) VALUES (?,?,?,?,?)",
                (achat_id, ligne.produit_id, ligne.quantite, ligne.prix_unitaire, ltotal)
            )
            db.execute("UPDATE produits SET quantite=quantite+?,prix_achat=?,updated_at=datetime('now') WHERE id=?", (ligne.quantite, ligne.prix_unitaire, ligne.produit_id))
            db.execute(
                "INSERT INTO mouvements_stock (produit_id,type,quantite,reference,magasin_id) VALUES (?,?,?,?,?)",
                (ligne.produit_id, "entree", ligne.quantite, numero, a.magasin_id)
            )

        db.commit()
        return {"id": achat_id, "numero": numero, "total": total, "message": "Achat enregistré"}
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    finally:
        db.close()
