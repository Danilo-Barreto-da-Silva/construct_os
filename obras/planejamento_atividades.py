"""Telas do planejamento físico ponderado, separadas do legado por apartamentos."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from .curva_s import cadastrar_servico, consolidar_curva, registrar_marco
from .forms import MarcoServicoForm, ServicoObraForm
from .models import EventoMarcoServico, MarcoServico, Torre


@login_required(login_url='login_sistema')
def planejamento_fisico(request):
    torres = Torre.objects.order_by('nome')
    torre_param = request.GET.get('torre', '')
    if not torre_param.isdecimal():
        torre_param = ''
    torre = torres.filter(pk=int(torre_param)).first() if torre_param else torres.first()

    servico_form = ServicoObraForm(initial={'torre': torre})
    marco_form = MarcoServicoForm(
        torre=torre,
        initial={'mes_referencia': timezone.localdate().strftime('%Y-%m')},
    )

    if request.method == 'POST':
        if not request.user.is_staff:
            raise PermissionDenied('Somente equipe autorizada pode alterar planejamento físico.')
        acao = request.POST.get('acao')
        if acao == 'servico':
            servico_form = ServicoObraForm(request.POST)
            if servico_form.is_valid():
                dados = servico_form.cleaned_data
                try:
                    servico = cadastrar_servico(
                        autor=request.user, torre=dados['torre'], codigo=dados['codigo'],
                        descricao=dados['descricao'], peso_percentual=dados['peso_percentual'],
                    )
                except ValidationError as exc:
                    servico_form.add_error(None, exc)
                else:
                    messages.success(request, 'Serviço cadastrado com seu peso físico.')
                    return redirect(
                        reverse('planejamento_fisico') + f'?torre={servico.torre_id}'
                    )
        elif acao == 'marco':
            servico_id = request.POST.get('servico', '')
            mes_postado = request.POST.get('mes_referencia', '')
            existente = None
            if servico_id.isdecimal() and len(mes_postado) == 7:
                existente = MarcoServico.objects.filter(
                    servico_id=int(servico_id), mes_referencia=mes_postado,
                    servico__torre=torre,
                ).first()
            # Uma revisão deve validar contra a instância existente para
            # não disparar incorretamente a restrição única de serviço/mês.
            marco_form = MarcoServicoForm(request.POST, instance=existente, torre=torre)
            if marco_form.is_valid():
                dados = marco_form.cleaned_data
                try:
                    marco, alterou = registrar_marco(
                        autor=request.user, servico=dados['servico'],
                        mes_referencia=dados['mes_referencia'],
                        previsto_acumulado=dados['previsto_acumulado'],
                        realizado_acumulado=dados['realizado_acumulado'],
                        observacao=dados['observacao'],
                    )
                except ValidationError as exc:
                    marco_form.add_error(None, exc)
                else:
                    if alterou:
                        messages.success(request, 'Acumulados salvos e revisão registrada no histórico.')
                    else:
                        messages.info(request, 'Nenhuma mudança de percentual; lançamento já estava atualizado.')
                    return redirect(
                        reverse('planejamento_fisico') + f'?torre={marco.servico.torre_id}'
                    )
        else:
            messages.error(request, 'Operação de planejamento desconhecida.')

    curva = consolidar_curva(torre) if torre is not None else None
    marcos = (
        MarcoServico.objects.filter(servico__torre=torre)
        .select_related('servico', 'atualizado_por')
        .order_by('-mes_referencia', 'servico__codigo')
        if torre else MarcoServico.objects.none()
    )
    eventos = (
        EventoMarcoServico.objects.filter(marco__servico__torre=torre)
        .select_related('marco__servico', 'autor').order_by('-criado_em', '-id')[:30]
        if torre else []
    )
    return render(request, 'obras/planejamento_fisico.html', {
        'torres': torres, 'torre': torre, 'servico_form': servico_form,
        'marco_form': marco_form, 'curva': curva, 'marcos': marcos,
        'eventos': eventos, 'pode_editar': request.user.is_staff,
    }, status=200)
