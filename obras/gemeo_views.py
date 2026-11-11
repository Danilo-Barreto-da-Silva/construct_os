"""Prévia 3D conceitual para apresentação interna.

O modelo é geometria SINTÉTICA e não é extraído de BIM, DWG, PDF nem vídeo.
Nunca registra medições, não muda FVS e não envia dados a provedores de IA.
"""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import UnidadeInteligente, VistoriaInteligente, validar_mes_referencia
from .parametros import progresso_unidade


@login_required(login_url='login_sistema')
@never_cache
def gemeo_conceitual(request, apartamento_id):
    # Enquanto não houver isolamento por construtora/obra, somente equipe staff.
    if not request.user.is_staff:
        raise PermissionDenied('Prévia 3D disponível somente para demonstração técnica autorizada.')
    cfg = get_object_or_404(
        UnidadeInteligente.objects.select_related('apartamento__torre', 'tipologia'),
        apartamento_id=apartamento_id, ativo=True
    )
    mes = request.GET.get('mes', timezone.localdate().strftime('%Y-%m'))
    try:
        validar_mes_referencia(mes)
    except ValidationError:
        mes = timezone.localdate().strftime('%Y-%m')
    progresso = progresso_unidade(cfg, mes)
    ultima = (
        VistoriaInteligente.objects.filter(apartamento=cfg.apartamento)
        .order_by('-criado_em', '-pk').first()
    )
    outras = (
        UnidadeInteligente.objects.filter(tipologia=cfg.tipologia, ativo=True)
        .select_related('apartamento')
        .order_by('apartamento__andar', 'apartamento__numero')[:20]
    )
    return render(request, 'obras/gemeo_conceitual.html', {
        'cfg': cfg, 'mes': mes, 'progresso': progresso,
        'vistoria': ultima, 'outras': outras,
    })
