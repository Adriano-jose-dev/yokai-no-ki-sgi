"""
Núcleo de autenticação — SGI-YKR (Fase A / Requisito 6).

Concentra:
- hash e verificação de senha (bcrypt via passlib);
- criação e decodificação de tokens JWT (com `sub` e `role`);
- dependências FastAPI `get_usuario_atual` e `requer_papel(*roles)`.

O `role` viaja no token, então adicionar um papel `sensei` restrito ao Tatame no
futuro não exige redesenho: basta proteger a rota com `requer_papel("admin",
"sensei")`.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import config
from database import get_db
from models import Usuario

# Contexto de hash de senha (bcrypt).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Extrai o token do header Authorization: Bearer <token>.
# tokenUrl é apenas informativo para o Swagger (a rota real é POST /auth/login).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

ALGORITHM = "HS256"


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha_pura: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_pura, senha_hash)


def criar_access_token(sub: str, role: str) -> str:
    """Emite um JWT com `sub` (username), `role` e expiração da configuração."""
    expira = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MIN)
    payload = {"sub": sub, "role": role, "exp": expira}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Decodifica e valida o JWT. Lança 401 se inválido ou expirado."""
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado ou token inválido.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise credenciais_invalidas


def get_usuario_atual(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Usuario:
    """Dependência: valida o token e retorna o usuário ativo correspondente."""
    payload = decodificar_token(token)
    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado ou token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inexistente ou inativo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def requer_papel(*roles: str):
    """Fábrica de dependência: exige que o usuário atual tenha um dos papéis.

    Uso: `Depends(requer_papel("admin"))`. Retorna 403 se o papel não bater.
    Pronta para o futuro `sensei`: `Depends(requer_papel("admin", "sensei"))`.
    """

    def _verificador(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para este recurso.",
            )
        return usuario

    return _verificador
