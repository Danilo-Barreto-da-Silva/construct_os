"""Protege também o login nativo do Django Admin contra força bruta.

Não altera o tratamento de outros endpoints nem registra dados pessoais.
"""
import logging

from django.http import HttpResponse
from django.urls import reverse

from .seguranca_login import esta_bloqueado, registrar_falha, registrar_sucesso


logger = logging.getLogger(__name__)


class LimiteTentativasAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != 'POST' or request.path_info != reverse('admin:login'):
            return self.get_response(request)
        if request.user.is_authenticated:
            return self.get_response(request)

        usuario = request.POST.get('username', '').strip()
        if esta_bloqueado(request, usuario):
            logger.warning('Login administrativo bloqueado temporariamente.')
            resp = HttpResponse(
                'Muitas tentativas de acesso. Aguarde até 15 minutos e tente novamente.',
                content_type='text/plain; charset=utf-8', status=429,
            )
            resp['Retry-After'] = '900'
            resp['Cache-Control'] = 'no-store'
            return resp

        resposta = self.get_response(request)
        if request.user.is_authenticated:
            registrar_sucesso(request, usuario)
        elif resposta.status_code == 200:
            # Só contabilizar formulário com credenciais rejeitadas, não falha
            # inesperada do servidor nem erro de validação CSRF.
            registrar_falha(request, usuario)
        return resposta
