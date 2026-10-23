"""회원가입 · 로그인 · 아이디/비밀번호 찾기 (MongoDB `users`, `auth_sessions` 컬렉션).

- 비밀번호는 PBKDF2-SHA256(+개별 salt)로 해시해서 저장합니다. 원문은 저장하지 않습니다.
- 로그인하면 임의 토큰을 발급하고, 토큰의 해시만 DB에 저장합니다(7일 유효).
- 비밀번호를 5회 틀리면 5분간 잠깁니다.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

PBKDF2_ITER = 200_000
SESSION_DAYS = 7
MAX_FAILS = 5
LOCK_MINUTES = 5
TERMS_VERSION = "2026-10"
PW_RULE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
EMAIL_RULE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ID_RULE = re.compile(r"^[A-Za-z0-9_\-.]{4,20}$")


def now():
    return datetime.now(timezone.utc)


def hash_pw(pw: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, PBKDF2_ITER)
    return f"pbkdf2${PBKDF2_ITER}${salt.hex()}${h.hex()}"


def verify_pw(pw: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


def token_hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def mask_id(uid: str) -> str:
    return uid[:2] + "*" * max(2, len(uid) - 2) if len(uid) > 2 else uid[:1] + "*"


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


class SignupIn(BaseModel):
    user_id: str = ""
    password: str = ""
    email: str = ""
    name: str = ""
    phone: str = ""
    address: str = ""
    address_detail: str = ""
    birth: str = ""          # YYYY-MM-DD (선택)
    agreed_terms: bool = False


class LoginIn(BaseModel):
    user_id: str = ""
    password: str = ""


class FindIdIn(BaseModel):
    email: str = ""
    phone: str = ""


class ResetIn(BaseModel):
    user_id: str = ""
    email: str = ""
    new_password: str = ""


def make_auth_router(db):
    r = APIRouter(prefix="/auth", tags=["auth"])
    users, sessions = db["users"], db["auth_sessions"]
    state = {"indexed": False}

    def ensure_indexes():
        if state["indexed"]:
            return
        try:
            users.create_index("user_id", unique=True)
            users.create_index("email", unique=True)
            sessions.create_index("token_hash", unique=True)
            sessions.create_index("expires_at", expireAfterSeconds=0)   # 만료된 세션 자동 삭제
            state["indexed"] = True
        except Exception as e:
            print("users 인덱스 생성 실패:", e)

    def public(u):
        return {"user_id": u["user_id"], "name": u.get("name", ""), "email": u.get("email", "")}

    def current_user(authorization: Optional[str]):
        if not authorization or not authorization.lower().startswith("bearer "):
            return None
        s = sessions.find_one({"token_hash": token_hash(authorization[7:].strip())})
        if not s or s["expires_at"].replace(tzinfo=timezone.utc) < now():
            return None
        return users.find_one({"user_id": s["user_id"]})

    @r.post("/signup", status_code=201)
    def signup(b: SignupIn):
        ensure_indexes()
        uid, email, name = b.user_id.strip(), b.email.strip().lower(), b.name.strip()
        if not b.agreed_terms:
            raise HTTPException(400, "필수 약관에 동의해 주세요.")
        if not ID_RULE.match(uid):
            raise HTTPException(400, "아이디는 영문·숫자·_-. 4~20자로 입력해 주세요.")
        if not PW_RULE.match(b.password):
            raise HTTPException(400, "비밀번호는 8자리 이상의 대소문자, 숫자, 특수문자를 포함해야 해요.")
        if not EMAIL_RULE.match(email):
            raise HTTPException(400, "이메일 주소를 확인해 주세요.")
        if not name:
            raise HTTPException(400, "이름을 입력해 주세요.")
        if users.find_one({"user_id": uid}):
            raise HTTPException(409, "이미 사용 중인 아이디예요.")
        if users.find_one({"email": email}):
            raise HTTPException(409, "이미 가입된 이메일이에요.")
        doc = {
            "user_id": uid, "password_hash": hash_pw(b.password), "email": email, "name": name,
            "phone": digits(b.phone), "address": b.address.strip(), "address_detail": b.address_detail.strip(),
            "birth": b.birth.strip(), "terms_agreed_at": now(), "terms_version": TERMS_VERSION,
            "created_at": now(), "failed_logins": 0, "locked_until": None,
        }
        try:
            users.insert_one(doc)
        except Exception:      # 동시에 같은 아이디/이메일로 가입한 경우(유니크 인덱스)
            raise HTTPException(409, "이미 사용 중인 아이디 또는 이메일이에요.")
        return {"success": True, "user": public(doc)}

    @r.get("/check-id")
    def check_id(user_id: str):
        uid = user_id.strip()
        if not ID_RULE.match(uid):
            return {"available": False, "message": "영문·숫자·_-. 4~20자로 입력해 주세요."}
        taken = users.find_one({"user_id": uid}) is not None
        return {"available": not taken, "message": "이미 사용 중인 아이디예요." if taken else "사용할 수 있는 아이디예요."}

    @r.post("/login")
    def login(b: LoginIn):
        uid = b.user_id.strip()
        u = users.find_one({"user_id": uid}) if uid else None
        bad = HTTPException(401, "아이디 또는 비밀번호가 올바르지 않아요.")
        if not u:
            raise bad
        lock = u.get("locked_until")
        if lock and lock.replace(tzinfo=timezone.utc) > now():
            raise HTTPException(429, f"로그인 시도가 너무 많아요. {LOCK_MINUTES}분 뒤에 다시 시도해 주세요.")
        if not verify_pw(b.password, u["password_hash"]):
            fails = u.get("failed_logins", 0) + 1
            upd = {"failed_logins": fails}
            if fails >= MAX_FAILS:
                upd = {"failed_logins": 0, "locked_until": now() + timedelta(minutes=LOCK_MINUTES)}
            users.update_one({"_id": u["_id"]}, {"$set": upd})
            raise bad
        users.update_one({"_id": u["_id"]}, {"$set": {"failed_logins": 0, "locked_until": None, "last_login_at": now()}})
        token = secrets.token_urlsafe(32)
        sessions.insert_one({"token_hash": token_hash(token), "user_id": uid, "created_at": now(),
                             "expires_at": now() + timedelta(days=SESSION_DAYS)})
        return {"success": True, "token": token, "user": public(u)}

    @r.get("/me")
    def me(authorization: Optional[str] = Header(default=None)):
        u = current_user(authorization)
        if not u:
            raise HTTPException(401, "로그인이 필요해요.")
        return {"user": public(u)}

    @r.post("/logout")
    def logout(authorization: Optional[str] = Header(default=None)):
        if authorization and authorization.lower().startswith("bearer "):
            sessions.delete_one({"token_hash": token_hash(authorization[7:].strip())})
        return {"success": True}

    @r.post("/find-id")
    def find_id(b: FindIdIn):
        """이메일 또는 휴대폰으로 가입 아이디를 찾아 일부를 가려서 알려줍니다."""
        q = None
        if b.email.strip():
            q = {"email": b.email.strip().lower()}
        elif digits(b.phone):
            q = {"phone": digits(b.phone)}
        if not q:
            raise HTTPException(400, "이메일 또는 휴대폰 번호를 입력해 주세요.")
        u = users.find_one(q)
        if not u:
            raise HTTPException(404, "일치하는 회원 정보를 찾지 못했어요.")
        return {"success": True, "masked_id": mask_id(u["user_id"])}

    @r.post("/reset-password")
    def reset_password(b: ResetIn):
        """아이디 + 가입 이메일이 일치하면 새 비밀번호로 변경합니다(이메일 발송 서버가 없는 시연용 방식)."""
        if not PW_RULE.match(b.new_password):
            raise HTTPException(400, "비밀번호는 8자리 이상의 대소문자, 숫자, 특수문자를 포함해야 해요.")
        u = users.find_one({"user_id": b.user_id.strip(), "email": b.email.strip().lower()})
        if not u:
            raise HTTPException(404, "아이디와 가입 이메일이 일치하는 회원을 찾지 못했어요.")
        users.update_one({"_id": u["_id"]}, {"$set": {"password_hash": hash_pw(b.new_password), "failed_logins": 0,
                                                     "locked_until": None, "password_changed_at": now()}})
        sessions.delete_many({"user_id": u["user_id"]})      # 기존 로그인은 모두 해제
        return {"success": True}

    return r
