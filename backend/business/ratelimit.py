"""
Rate limiting de login — SGI-YKR (S3 do plano de segurança).

Limitador simples **em memória** para frear ataques de força bruta no
`POST /auth/login`, sem adicionar dependência externa. Para o MVP (processo
único) é suficiente; numa topologia multi-processo/produção, trocar por um
backend compartilhado (ex.: Redis) é o passo natural.

Regra: até `MAX_TENTATIVAS` falhas numa janela de `JANELA_SEG` segundos. Ao
exceder, a chave fica bloqueada por `BLOQUEIO_SEG` segundos. Um login com
sucesso limpa o contador daquela chave.

A chave combina usuário + IP, para não deixar um atacante bloquear a conta de
um terceiro só martelando o username (e também não liberar trocando de IP).
"""

from __future__ import annotations

import time

MAX_TENTATIVAS = 5
JANELA_SEG = 5 * 60       # 5 minutos
BLOQUEIO_SEG = 15 * 60    # 15 minutos

# chave -> {"tentativas": [timestamps], "bloqueado_ate": float|None}
_registro: dict[str, dict] = {}


def _chave(usuario: str, ip: str) -> str:
    return f"{(usuario or '?').lower()}|{ip or '?'}"


def esta_bloqueado(usuario: str, ip: str, agora: float | None = None) -> int:
    """Retorna os segundos restantes de bloqueio (0 se não está bloqueado)."""
    agora = agora if agora is not None else time.time()
    dados = _registro.get(_chave(usuario, ip))
    if not dados:
        return 0
    ate = dados.get("bloqueado_ate")
    if ate and ate > agora:
        return int(ate - agora)
    return 0


def registrar_falha(usuario: str, ip: str, agora: float | None = None) -> bool:
    """Registra uma tentativa falha. Retorna `True` se passou a bloquear agora.

    Mantém só as tentativas dentro da janela; ao atingir o limite, marca o
    bloqueio.
    """
    agora = agora if agora is not None else time.time()
    chave = _chave(usuario, ip)
    dados = _registro.setdefault(chave, {"tentativas": [], "bloqueado_ate": None})

    # Descarta tentativas fora da janela.
    dados["tentativas"] = [
        t for t in dados["tentativas"] if agora - t < JANELA_SEG
    ]
    dados["tentativas"].append(agora)

    if len(dados["tentativas"]) >= MAX_TENTATIVAS:
        dados["bloqueado_ate"] = agora + BLOQUEIO_SEG
        return True
    return False


def registrar_sucesso(usuario: str, ip: str) -> None:
    """Limpa o contador da chave após um login bem-sucedido."""
    _registro.pop(_chave(usuario, ip), None)


def resetar() -> None:
    """Zera o estado (uso em testes)."""
    _registro.clear()
