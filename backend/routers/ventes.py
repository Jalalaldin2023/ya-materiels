from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from datetime import datetime

router = APIRouter()


class LigneIn(BaseModel):
    produit_id: int
    quantite: int
    prix_unitaire: float


class VenteIn(BaseModel):
    magasin_id: int
    caissier_id: Optional[int] = None
    client_id: Optional[int] = None
    lignes: List[LigneIn]
    remise: float = 0
    montant_paye: float = 0
    mode_paiement: str = "especes"
    statut: str = "payee"
    notes: Optional[str] = None


def gen_numero(magasin_id, db):
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"VT{magasin_id}-{today}"
    count = db.execute("SELECT COUNT(*) FROM ventes WHERE numero LIKE ?", (f"{prefix}%",)).fetchone()[0]
    return f"{prefix}-{count+1:03d}"


@router.get("")
def list_ventes(magasin_id: int, search: str = "", date_debut: str = "", date_fin: str = ""):
    db = get_db()
    q = """SELECT v.*, c.nom as client_nom, u.nom as caissier_nom
           FROM ventes v LEFT JOIN clients c ON v.client_id=c.id
           LEFT JOIN utilisateurs u ON v.caissier_id=u.id
           WHERE v.magasin_id=?"""
    params = [magasin_id]
    if search:
        q += " AND (v.numero LIKE ? OR c.nom LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if date_debut:
        q += " AND date(v.created_at)>=?"
        params.append(date_debut)
    if date_fin:
        q += " AND date(v.created_at)<=?"
        params.append(date_fin)
    q += " ORDER BY v.created_at DESC"
    rows = db.execute(q, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{vid}")
def get_vente(vid: int):
    db = get_db()
    vente = db.execute(
        "SELECT v.*, c.nom as client_nom, c.telephone as client_tel, u.nom as caissier_nom FROM ventes v LEFT JOIN clients c ON v.client_id=c.id LEFT JOIN utilisateurs u ON v.caissier_id=u.id WHERE v.id=?",
        (vid,)
    ).fetchone()
    if not vente:
        raise HTTPException(404, "Vente non trouvée")
    lignes = db.execute(
        "SELECT vl.*, p.nom as produit_nom, p.code as produit_code FROM vente_lignes vl JOIN produits p ON vl.produit_id=p.id WHERE vl.vente_id=?",
        (vid,)
    ).fetchall()
    db.close()
    return {**dict(vente), "lignes": [dict(l) for l in lignes]}


@router.post("")
def create_vente(v: VenteIn):
    db = get_db()
    try:
        for ligne in v.lignes:
            prod = db.execute("SELECT * FROM produits WHERE id=? AND magasin_id=?", (ligne.produit_id, v.magasin_id)).fetchone()
            if not prod:
                raise HTTPException(400, f"Produit {ligne.produit_id} non trouvé")
            if prod["quantite"] < ligne.quantite:
                raise HTTPException(400, f"Stock insuffisant pour {prod['nom']}: {prod['quantite']} disponible(s)")

        total = sum(l.quantite * l.prix_unitaire for l in v.lignes) - v.remise
        numero = gen_numero(v.magasin_id, db)
        statut = "credit" if v.montant_paye < total else v.statut

        cur = db.execute(
            "INSERT INTO ventes (numero,client_id,total,remise,montant_paye,mode_paiement,statut,notes,magasin_id,caissier_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (numero, v.client_id, total, v.remise, v.montant_paye, v.mode_paiement, statut, v.notes, v.magasin_id, v.caissier_id)
        )
        vente_id = cur.lastrowid

        for ligne in v.lignes:
            ltotal = ligne.quantite * ligne.prix_unitaire
            db.execute(
                "INSERT INTO vente_lignes (vente_id,produit_id,quantite,prix_unitaire,total) VALUES (?,?,?,?,?)",
                (vente_id, ligne.produit_id, ligne.quantite, ligne.prix_unitaire, ltotal)
            )
            db.execute("UPDATE produits SET quantite=quantite-?, updated_at=datetime('now') WHERE id=?", (ligne.quantite, ligne.produit_id))
            db.execute(
                "INSERT INTO mouvements_stock (produit_id,type,quantite,reference,magasin_id) VALUES (?,?,?,?,?)",
                (ligne.produit_id, "sortie", ligne.quantite, numero, v.magasin_id)
            )

        if v.client_id and statut == "credit":
            db.execute("UPDATE clients SET solde=solde+(?) WHERE id=?", (total - v.montant_paye, v.client_id))

        db.commit()
        return {"id": vente_id, "numero": numero, "total": total, "message": "Vente enregistrée"}
    except HTTPException:
        db.rollback(); raise
    except Exception as e:
        db.rollback(); raise HTTPException(400, str(e))
    finally:
        db.close()


@router.delete("/{vid}")
def cancel_vente(vid: int):
    db = get_db()
    try:
        vente = db.execute("SELECT * FROM ventes WHERE id=?", (vid,)).fetchone()
        if not vente:
            raise HTTPException(404, "Vente non trouvée")
        lignes = db.execute("SELECT * FROM vente_lignes WHERE vente_id=?", (vid,)).fetchall()
        for l in lignes:
            db.execute("UPDATE produits SET quantite=quantite+? WHERE id=?", (l["quantite"], l["produit_id"]))
            db.execute(
                "INSERT INTO mouvements_stock (produit_id,type,quantite,reference,notes,magasin_id) VALUES (?,?,?,?,?,?)",
                (l["produit_id"], "entree", l["quantite"], vente["numero"], "Annulation", vente["magasin_id"])
            )
        db.execute("DELETE FROM ventes WHERE id=?", (vid,))
        db.commit()
        return {"message": "Vente annulée"}
    finally:
        db.close()
