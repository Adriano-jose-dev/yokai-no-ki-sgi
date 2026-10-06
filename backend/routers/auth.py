"""
Rotas de autenticação — SGI-YKR (Fase A / Requisito 6 + hardening S2/S3).

- POST /auth/login: valida credenciais (formulário OAuth2 padrão) e emite um
  JWT. Protegido por **rate limiting** (S3) contra força bruta.
- POST /auth/trocar-senha: troca a senha do usuário autenticado, exigindo a
  senha atual e validando a força da nova (S2); limpa a flag de troca
  obrigatória.

Padrão OAuth2 "password flow": o corpo do login é
`application/x-www-form-urlencoded` com os campos `username` e `password`.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import TokenResponse, TrocarSenhaRequest
from business.auth import (
    verificar_senha,
    criar_access_token,
    hash_senha,
    validar_forca_senha,
    get_usuario_atual,
)
from business import ratelimit
from business import auditoria

router = APIRouter(tags=["Autenticação"])


def _ip_do_request(request: Request) -> str:
    """IP de origem (considera proxy via X-Forwarded-For, se presente)."""
    encaminhado = request.headers.get("x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.client.host if request.client else "?"


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Autenticar e obter token JWT (OAuth2 password flow)",
    description=(
        "Valida usuário e senha da diretoria e, em caso de sucesso, emite um "
        "token JWT contendo `sub` (username) e `role`.\n\n"
        "Segue o **OAuth2 password flow** (`application/x-www-form-urlencoded` "
        "com `username` e `password`).\n\n"
        "- Senha verificada contra o hash **bcrypt**.\n"
        "- Credenciais inválidas: **401** com mensagem genérica.\n"
        "- Usuário inativo: **401**.\n"
        "- **Rate limiting**: após várias tentativas falhas, novas tentativas "
        "recebem **429 (Too Many Requests)** por um período.\n\n"
        "O campo `precisa_trocar_senha` indica se o usuário deve trocar a senha "
        "antes de usar o sistema."
    ),
)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    ip = _ip_do_request(request)

    # S3: barra tentativas quando a chave usuário+IP está bloqueada.
    restante = ratelimit.esta_bloqueado(form.username, ip)
    if restante > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Muitas tentativas de login. Tente novamente em "
                f"{restante // 60 + 1} minuto(s)."
            ),
        )

    usuario = db.query(Usuario).filter(Usuario.username == form.username).first()

    # Mensagem genérica: não revela se o erro foi no usuário ou na senha.
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        bloqueou = ratelimit.registrar_falha(form.username, ip)
        if bloqueou:
            # Bloqueio é evento sensível de segurança — registra na auditoria.
            auditoria.registrar(
                db,
                acao="login_bloqueado",
                autor=form.username,
                descricao=f"Login bloqueado por força bruta (IP {ip}).",
                categoria="sensivel",
            )
            db.commit()
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

    # Sucesso: limpa o contador de tentativas desta chave.
    ratelimit.registrar_sucesso(form.username, ip)

    token = criar_access_token(sub=usuario.username, role=usuario.role)
    return TokenResponse(
        access_token=token,
        precisa_trocar_senha=bool(usuario.precisa_trocar_senha),
    )


@router.post(
    "/auth/trocar-senha",
    summary="Trocar a própria senha (exige autenticação)",
    description=(
        "Troca a senha do usuário autenticado. Exige a **senha atual** e valida "
        "a **força** da nova senha (mínimo de 10 caracteres, misturando tipos). "
        "Ao concluir, limpa a flag de troca obrigatória (`precisa_trocar_senha`)."
    ),
)
def trocar_senha(
    req: TrocarSenhaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    if not verificar_senha(req.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    ok, motivo = validar_forca_senha(req.nova_senha)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Senha fraca: {motivo}.")

    if verificar_senha(req.nova_senha, usuario.senha_hash):
        raise HTTPException(
            status_code=400, detail="A nova senha deve ser diferente da atual."
        )

    usuario.senha_hash = hash_senha(req.nova_senha)
    usuario.precisa_trocar_senha = False
    auditoria.registrar(
        db,
        acao="trocar_senha",
        autor=usuario.username,
        descricao="Senha alterada pelo próprio usuário.",
        categoria="sensivel",
    )
    db.commit()
    return {"status": "Senha alterada com sucesso"}
