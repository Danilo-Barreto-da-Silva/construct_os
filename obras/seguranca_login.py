"""Mitigação de tentativas repetidas de login (sem armazenar senha ou username).

Uma mesma combinação conta/IP é limitada a 5 falhas por 15 minutos;
o IP sozinho fica limitado a 20 falhas nesse período.
O cache precisa ser COMPARTILHADO entre workers em produção (ex.: Redis).
Não usar cabeçalhos X-Forwarded-For fornecidos pelo cliente.
"""
import hashlib
import hmac

from django.conf import settings
from django.core.cache import cache

DURACAO = 15 * 60
LIMITE_CONTA_IP = 5
LIMITE_IP = 20


def _chaves(request, usuario):
    ip = request.META.get('REMOTE_ADDR', '') or 'ip-desconhecido'
    usuario_normalizado = usuario.strip().casefold()
    secret = settings.SECRET_KEY.encode('utf-8')

    def chave(sufixo, valor):
        digest = hmac.new(
            secret, (sufixo + ':' + valor).encode('utf-8'), hashlib.sha256
        ).hexdigest()
        return 'sgo:autenticacao:' + sufixo + ':' + digest

    return (
        chave('conta-ip', usuario_normalizado + '|' + ip),
        chave('ip', ip),
    )


def esta_bloqueado(request, usuario):
    conta_ip, ip = _chaves(request, usuario)
    return (
        int(cache.get(conta_ip, 0)) >= LIMITE_CONTA_IP
        or int(cache.get(ip, 0)) >= LIMITE_IP
    )


def registrar_falha(request, usuario):
    """TTL fixo desde a primeira falha; incremento atômico onde o cache suporta."""
    for chave in _chaves(request, usuario):
        if cache.add(chave, 1, timeout=DURACAO):
            continue
        try:
            cache.incr(chave)
        except ValueError:
            # A entrada expirou entre add e incr.
            cache.add(chave, 1, timeout=DURACAO)


def registrar_sucesso(request, usuario):
    # O contador geral do IP permanece: previne tentativas em contas diferentes.
    conta_ip, _ = _chaves(request, usuario)
    cache.delete(conta_ip)
