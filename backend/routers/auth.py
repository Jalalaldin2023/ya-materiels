import hashlib
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db, hash_pwd

class ChangePasswordIn(BaseModel):
    new_password: str

router = APIRouter()


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(BaseModel):
    nom: str
    username: str
    password: Optional[str] = None
    role: str = "caissier"
    magasin_id: Optional[int] = None
    actif: int = 1
    permissions: Optional[List[str]] = None  # liste des modules autorisés


class MagasinIn(BaseModel):
    nom: str
    slogan: Optional[str] = ""
    adresse: Optional[str] = ""
    telephone: Optional[str] = ""
    email: Optional[str] = ""
    rccm: Optional[str] = ""
    nif: Optional[str] = ""
    logo: Optional[str] = ""
    photo: Optional[str] = ""
    devise: Optional[str] = "FCFA"
    theme_primary: Optional[str] = "#1a56db"
    theme_sidebar: Optional[str] = "#1e293b"
    recu_pied: Optional[str] = "Merci pour votre achat !"


# ── Auth ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(data: LoginIn):
    db = get_db()
    user = db.execute(
        "SELECT * FROM utilisateurs WHERE username=? AND actif=1", (data.username,)
    ).fetchone()
    db.close()
    if not user or user["password"] != hash_pwd(data.password):
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")
    perms = []
    try:
        raw = user["permissions"] or ""
        if raw:
            perms = json.loads(raw)
    except Exception:
        perms = []
    return {
        "id": user["id"],
        "nom": user["nom"],
        "username": user["username"],
        "role": user["role"],
        "magasin_id": user["magasin_id"],
        "permissions": perms,
        "password_changed": user["password_changed"] if "password_changed" in user.keys() else 1,
    }


# ── Magasins ────────────────────────────────────────────────────────────────

@router.get("/magasins")
def list_magasins():
    db = get_db()
    rows = db.execute("SELECT * FROM magasins ORDER BY id").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/magasins/{mid}")
def get_magasin(mid: int):
    db = get_db()
    row = db.execute("SELECT * FROM magasins WHERE id=?", (mid,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Magasin non trouvé")
    return dict(row)


@router.post("/magasins")
def create_magasin(m: MagasinIn):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO magasins (nom,slogan,adresse,telephone,email,rccm,nif,logo,photo,devise,theme_primary,theme_sidebar,recu_pied) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (m.nom, m.slogan, m.adresse, m.telephone, m.email, m.rccm, m.nif, m.logo, m.photo, m.devise, m.theme_primary, m.theme_sidebar, m.recu_pied)
        )
        mid = cur.lastrowid
        cats = ["Outils","Visserie","Plomberie","Électricité","Peinture","Bois","Quincaillerie","Autre"]
        db.executemany("INSERT INTO categories (nom,magasin_id) VALUES (?,?)", [(c,mid) for c in cats])
        db.commit()
        return {"id": mid, "message": "Magasin créé"}
    finally:
        db.close()


@router.put("/magasins/{mid}")
def update_magasin(mid: int, m: MagasinIn):
    db = get_db()
    try:
        db.execute(
            "UPDATE magasins SET nom=?,slogan=?,adresse=?,telephone=?,email=?,rccm=?,nif=?,logo=?,photo=?,devise=?,theme_primary=?,theme_sidebar=?,recu_pied=? WHERE id=?",
            (m.nom, m.slogan, m.adresse, m.telephone, m.email, m.rccm, m.nif, m.logo, m.photo, m.devise, m.theme_primary, m.theme_sidebar, m.recu_pied, mid)
        )
        db.commit()
        return {"message": "Magasin mis à jour"}
    finally:
        db.close()


# ── Utilisateurs ─────────────────────────────────────────────────────────────

@router.get("/utilisateurs")
def list_users():
    db = get_db()
    rows = db.execute(
        "SELECT u.id, u.nom, u.username, u.role, u.magasin_id, u.actif, u.permissions, u.created_at, m.nom as magasin_nom FROM utilisateurs u LEFT JOIN magasins m ON u.magasin_id=m.id ORDER BY u.nom"
    ).fetchall()
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['permissions'] = json.loads(d['permissions'] or '[]')
        except Exception:
            d['permissions'] = []
        result.append(d)
    return result


@router.post("/utilisateurs")
def create_user(u: UserIn):
    db = get_db()
    try:
        pwd = hash_pwd(u.password or "password123")
        perms_json = json.dumps(u.permissions or [])
        cur = db.execute(
            "INSERT INTO utilisateurs (nom, username, password, role, magasin_id, actif, permissions, password_changed) VALUES (?,?,?,?,?,?,?,0)",
            (u.nom, u.username, pwd, u.role, u.magasin_id, u.actif, perms_json)
        )
        db.commit()
        return {"id": cur.lastrowid, "message": "Utilisateur créé"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/utilisateurs/{uid}")
def update_user(uid: int, u: UserIn):
    db = get_db()
    try:
        perms_json = json.dumps(u.permissions or [])
        if u.password:
            # Admin reset password → force user to change it on next login
            db.execute(
                "UPDATE utilisateurs SET nom=?,username=?,password=?,role=?,magasin_id=?,actif=?,permissions=?,password_changed=0 WHERE id=?",
                (u.nom, u.username, hash_pwd(u.password), u.role, u.magasin_id, u.actif, perms_json, uid)
            )
        else:
            db.execute(
                "UPDATE utilisateurs SET nom=?,username=?,role=?,magasin_id=?,actif=?,permissions=? WHERE id=?",
                (u.nom, u.username, u.role, u.magasin_id, u.actif, perms_json, uid)
            )
        db.commit()
        return {"message": "Utilisateur mis à jour"}
    finally:
        db.close()


@router.put("/utilisateurs/{uid}/change-password")
def change_password(uid: int, data: ChangePasswordIn):
    if not data.new_password or len(data.new_password) < 6:
        raise HTTPException(400, "Le mot de passe doit faire au moins 6 caractères")
    db = get_db()
    try:
        db.execute(
            "UPDATE utilisateurs SET password=?, password_changed=1 WHERE id=?",
            (hash_pwd(data.new_password), uid)
        )
        db.commit()
        return {"message": "Mot de passe changé"}
    finally:
        db.close()


@router.delete("/utilisateurs/{uid}")
def delete_user(uid: int):
    db = get_db()
    admins = db.execute("SELECT COUNT(*) FROM utilisateurs WHERE role='admin' AND actif=1").fetchone()[0]
    user = db.execute("SELECT role FROM utilisateurs WHERE id=?", (uid,)).fetchone()
    if user and user["role"] == "admin" and admins <= 1:
        db.close()
        raise HTTPException(400, "Impossible de supprimer le dernier administrateur")
    db.execute("DELETE FROM utilisateurs WHERE id=?", (uid,))
    db.commit()
    db.close()
    return {"message": "Utilisateur supprimé"}
