"""
Rotas de autenticação — SGI-YKR (Fase A / Requisito 6).

POST /auth/login: valida credenciais (formulário OAuth2 padrão) e emite um JWT.

Padrão OAuth2 "password flow": o corpo é `application/x-www-form-urlencoded`
com os campos `username` e `password` (e opcionalmente `grant_type`). Isso
torna a API compatível com o botão *Authorize* do Swagger e com clientes
oficiais (web, mobile/APK, etc.) sem formato proprietário.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import TokenResponse
from business.auth import verificar_senha, criar_access_token

router = APIRouter(tags=["Autenticação"])


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Autenticar e obter token JWT (OAuth2 password flow)",
    description=(
        "Valida usuário e senha da diretoria e, em caso de sucesso, emite um "
        "token JWT contendo `sub` (username) e `role`, com expiração definida "
        "na configuração.\n\n"
        "Segue o **OAuth2 password flow**: envie o corpo como "
        "`application/x-www-form-urlencoded` com os campos `username` e "
        "`password`. Compatível com o botão *Authorize* do Swagger.\n\n"
        "- A senha é verificada contra o hash **bcrypt** armazenado.\n"
        "- Em credenciais inválidas retorna **401** com mensagem genérica "
        "(não revela se o erro foi no usuário ou na senha).\n"
        "- Usuário inativo também recebe **401**.\n\n"
        "Use o token retornado no header `Authorization: Bearer <token>` para "
        "acessar as demais rotas."
    ),
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    usuario = db.query(Usuario).filter(Usuario.username == form.username).first()

    # Mensagem genérica: não revela se o erro foi no usuário ou na senha.
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = criar_access_token(sub=usuario.username, role=usuario.role)
    return TokenResponse(access_token=token)
