from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class ProduitIn(BaseModel):
    code: Optional[str] = None
    nom: str
    description: Optional[str] = None
    categorie_id: Optional[int] = None
    fournisseur_id: Optional[int] = None
    prix_achat: float = 0
    prix_vente: float          # PV1 (+25%)
    prix_vente2: float = 0     # PV2 (+50%)
    prix_vente3: float = 0     # PV3 (+100%)
    transport: float = 0       # Frais de transport unitaire
    manutention: float = 0     # Frais de manutention unitaire
    quantite: int = 0
    quantite_min: int = 5
    unite: str = "pcs"
    magasin_id: int


class PrixRapideIn(BaseModel):
    prix_achat: Optional[float] = None
    prix_vente: Optional[float] = None
    prix_vente2: Optional[float] = None
    prix_vente3: Optional[float] = None
    transport: Optional[float] = None
    manutention: Optional[float] = None


@router.get("")
def list_produits(magasin_id: int, search: str = "", categorie_id: int = 0, stock_bas: bool = False):
    db = get_db()
    q = """SELECT p.*, c.nom as categorie_nom, f.nom as fournisseur_nom
           FROM produits p
           LEFT JOIN categories c ON p.categorie_id=c.id
           LEFT JOIN fournisseurs f ON p.fournisseur_id=f.id
           WHERE p.magasin_id=?"""
    params = [magasin_id]
    if search:
        q += " AND (p.nom LIKE ? OR p.code LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if categorie_id:
        q += " AND p.categorie_id=?"
        params.append(categorie_id)
    if stock_bas:
        q += " AND p.quantite <= p.quantite_min"
    q += " ORDER BY p.nom"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/categories")
def list_categories(magasin_id: int):
    db = get_db()
    rows = db.execute("SELECT * FROM categories WHERE magasin_id=? ORDER BY nom", (magasin_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{pid}")
def get_produit(pid: int):
    db = get_db()
    row = db.execute(
        "SELECT p.*, c.nom as categorie_nom FROM produits p LEFT JOIN categories c ON p.categorie_id=c.id WHERE p.id=?",
        (pid,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Produit non trouvé")
    return dict(row)


@router.post("")
def create_produit(p: ProduitIn):
    db = get_db()
    try:
        pv2 = p.prix_vente2 or round(p.prix_achat * 1.5 / 100) * 100
        pv3 = p.prix_vente3 or round(p.prix_achat * 2.0 / 100) * 100
        cur = db.execute(
            "INSERT INTO produits (code,nom,description,categorie_id,fournisseur_id,prix_achat,prix_vente,prix_vente2,prix_vente3,transport,manutention,quantite,quantite_min,unite,magasin_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (p.code, p.nom, p.description, p.categorie_id, p.fournisseur_id, p.prix_achat, p.prix_vente, pv2, pv3, p.transport, p.manutention, p.quantite, p.quantite_min, p.unite, p.magasin_id)
        )
        pid = cur.lastrowid
        if p.quantite > 0:
            db.execute(
                "INSERT INTO mouvements_stock (produit_id,type,quantite,notes,magasin_id) VALUES (?,?,?,?,?)",
                (pid, "entree", p.quantite, "Stock initial", p.magasin_id)
            )
        db.commit()
        return {"id": pid, "message": "Produit créé"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/{pid}")
def update_produit(pid: int, p: ProduitIn):
    db = get_db()
    try:
        pv2 = p.prix_vente2 or round(p.prix_achat * 1.5 / 100) * 100
        pv3 = p.prix_vente3 or round(p.prix_achat * 2.0 / 100) * 100
        db.execute(
            "UPDATE produits SET code=?,nom=?,description=?,categorie_id=?,fournisseur_id=?,prix_achat=?,prix_vente=?,prix_vente2=?,prix_vente3=?,transport=?,manutention=?,quantite_min=?,unite=?,updated_at=datetime('now') WHERE id=?",
            (p.code, p.nom, p.description, p.categorie_id, p.fournisseur_id, p.prix_achat, p.prix_vente, pv2, pv3, p.transport, p.manutention, p.quantite_min, p.unite, pid)
        )
        db.commit()
        return {"message": "Produit mis à jour"}
    finally:
        db.close()


@router.patch("/{pid}/prix")
def update_prix_rapide(pid: int, body: PrixRapideIn):
    """Mise à jour rapide des prix/coûts depuis les tableaux inline."""
    db = get_db()
    try:
        sets, vals = [], []
        if body.prix_achat  is not None: sets.append("prix_achat=?");  vals.append(body.prix_achat)
        if body.prix_vente  is not None: sets.append("prix_vente=?");  vals.append(body.prix_vente)
        if body.prix_vente2 is not None: sets.append("prix_vente2=?"); vals.append(body.prix_vente2)
        if body.prix_vente3 is not None: sets.append("prix_vente3=?"); vals.append(body.prix_vente3)
        if body.transport   is not None: sets.append("transport=?");   vals.append(body.transport)
        if body.manutention is not None: sets.append("manutention=?"); vals.append(body.manutention)
        if not sets:
            return {"message": "Rien à mettre à jour"}
        sets.append("updated_at=datetime('now')")
        vals.append(pid)
        db.execute(f"UPDATE produits SET {','.join(sets)} WHERE id=?", vals)
        db.commit()
        return {"message": "Prix mis à jour"}
    finally:
        db.close()


@router.delete("/{pid}")
def delete_produit(pid: int):
    db = get_db()
    db.execute("DELETE FROM produits WHERE id=?", (pid,))
    db.commit()
    db.close()
    return {"message": "Produit supprimé"}
