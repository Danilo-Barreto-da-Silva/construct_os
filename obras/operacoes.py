"""Páginas operacionais de qualidade e planejamento do Construct OS."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AbrirRNCForm, TratarRNCForm, ItemFVSForm, PlanejamentoMensalForm, TorreForm, ApartamentoForm, MedicaoMensalForm
from .models import (
    MedicaoMensal, NaoConformidade, ItemFVS,
    PlanejamentoMensal, Torre, Apartamento, HistoricoMedicao,
)
from .qualidade import abrir_rnc, atualizar_rnc, salvar_item_fvs


@login_required(login_url='login_sistema')
def lista_rncs(request):
    situacao = request.GET.get('situacao', 'PENDENTES')
    qs = NaoConformidade.objects.select_related(
        'medicao__apartamento__torre', 'responsavel', 'aberta_por'
    )
    if situacao == 'PENDENTES':
        qs = qs.exclude(situacao='RESOLVIDA')
    elif situacao in dict(NaoConformidade.SITUACOES):
        qs = qs.filter(situacao=situacao)
    elif situacao != 'TODAS':
        situacao = 'PENDENTES'
        qs = qs.exclude(situacao='RESOLVIDA')

    torre_id = request.GET.get('torre', '')
    if torre_id.isdecimal():
        qs = qs.filter(medicao__apartamento__torre_id=int(torre_id))
    else:
        torre_id = ''

    busca = request.GET.get('busca', '').strip()[:100]
    if busca:
        qs = qs.filter(
            Q(titulo__icontains=busca) |
            Q(medicao__apartamento__numero__icontains=busca) |
            Q(descricao__icontains=busca)
        )
    pagina = Paginator(qs, 30).get_page(request.GET.get('pagina'))
    # Os dados legados não representam automaticamente RNCs formalmente cadastradas.
    avisos_sem_rnc = MedicaoMensal.objects.filter(
        status_iso='NAO_CONFORME', rncs__isnull=True
    ).count()
    return render(request, 'obras/rncs_lista.html', {
        'pagina': pagina, 'situacao': situacao, 'busca': busca,
        'torre_id': torre_id, 'torres': Torre.objects.all(),
        'avisos_sem_rnc': avisos_sem_rnc,
    })


@login_required(login_url='login_sistema')
def abrir_rnc_pagina(request, medicao_id):
    medicao = get_object_or_404(
        MedicaoMensal.objects.select_related('apartamento__torre'), pk=medicao_id
    )
    if request.method == 'POST':
        form = AbrirRNCForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                rnc = abrir_rnc(
                    medicao.pk, autor=request.user,
                    titulo=dados['titulo'], descricao=dados['descricao'],
                    prioridade=dados['prioridade'],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, f'RNC #{rnc.pk} registrada e vinculada à medição.')
                return redirect('detalhe_rnc', rnc_id=rnc.pk)
    else:
        form = AbrirRNCForm(initial={
            'titulo': f'Não conformidade - Apto {medicao.apartamento.numero}',
        })
    return render(request, 'obras/rnc_abrir.html', {
        'medicao': medicao, 'form': form,
    })


@login_required(login_url='login_sistema')
def detalhe_rnc(request, rnc_id, form=None):
    rnc = get_object_or_404(
        NaoConformidade.objects.select_related(
            'medicao__apartamento__torre', 'responsavel',
            'aberta_por', 'encerrada_por'
        ),
        pk=rnc_id,
    )
    if form is None and request.user.is_staff:
        form = TratarRNCForm(instance=rnc)
    return render(request, 'obras/rnc_detalhe.html', {
        'rnc': rnc, 'form': form,
        'eventos': rnc.eventos.select_related('autor'),
        'pode_tratar': request.user.is_staff,
    })


@login_required(login_url='login_sistema')
@require_POST
def tratar_rnc(request, rnc_id):
    if not request.user.is_staff:
        raise PermissionDenied('Somente equipe autorizada pode atualizar uma RNC.')
    rnc = get_object_or_404(NaoConformidade, pk=rnc_id)
    form = TratarRNCForm(request.POST, instance=rnc)
    if form.is_valid():
        dados = form.cleaned_data
        try:
            atualizar_rnc(
                rnc.pk, autor=request.user,
                situacao=dados['situacao'],
                acao_corretiva=dados['acao_corretiva'],
                responsavel=dados['responsavel'],
                prazo=dados['prazo'],
                comentario=dados['comentario'],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f'RNC #{rnc.pk} atualizada e registrada no histórico.')
            return redirect('detalhe_rnc', rnc_id=rnc.pk)
    return detalhe_rnc(request, rnc_id, form=form)


@login_required(login_url='login_sistema')
def checklist_fvs(request, medicao_id):
    medicao = get_object_or_404(
        MedicaoMensal.objects.select_related(
            'apartamento__torre', 'fvs_aprovada_por'
        ),
        pk=medicao_id,
    )
    return render(request, 'obras/fvs_checklist.html', {
        'medicao': medicao,
        'itens': medicao.itens_fvs.select_related('verificado_por').all(),
        'form': ItemFVSForm(),
        'pode_aprovar': request.user.is_staff,
    })


@login_required(login_url='login_sistema')
@require_POST
def salvar_item_fvs_view(request, medicao_id, item_id=None):
    medicao = get_object_or_404(MedicaoMensal, pk=medicao_id)
    instance = (
        get_object_or_404(ItemFVS, pk=item_id, medicao=medicao)
        if item_id is not None else None
    )
    form = ItemFVSForm(request.POST, instance=instance)
    if form.is_valid():
        dados = form.cleaned_data
        try:
            salvar_item_fvs(
                medicao.pk, autor=request.user,
                descricao=dados['descricao'],
                resultado=dados['resultado'],
                observacao=dados['observacao'],
                item_id=item_id,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Item de inspeção salvo e registrado no histórico.')
            return redirect('checklist_fvs', medicao_id=medicao.pk)
    # Renderiza o mesmo formulário com mensagens de erro, sem perder as informações.
    return render(request, 'obras/fvs_checklist.html', {
        'medicao': medicao, 'form': form,
        'itens': medicao.itens_fvs.select_related('verificado_por').all(),
        'pode_aprovar': request.user.is_staff,
    }, status=400)


@login_required(login_url='login_sistema')
def planejamento(request):
    if request.method == 'POST' and not request.user.is_staff:
        raise PermissionDenied('Somente a equipe autorizada pode cadastrar metas.')

    form = PlanejamentoMensalForm()
    if request.method == 'POST':
        dados = request.POST
        torre_id = dados.get('torre', '')
        mes = dados.get('mes_referencia', '')
        existente = None
        if torre_id.isdecimal() and len(mes) == 7:
            existente = PlanejamentoMensal.objects.filter(
                torre_id=int(torre_id), mes_referencia=mes
            ).first()
        form = PlanejamentoMensalForm(request.POST, instance=existente)
        if form.is_valid():
            item = form.save(commit=False)
            item.registrado_por = request.user
            item.save()
            messages.success(request, 'Meta planejada salva para a torre e o mês.')
            return redirect('planejamento')

    metas = PlanejamentoMensal.objects.select_related(
        'torre', 'registrado_por'
    ).order_by('-mes_referencia', 'torre__nome')[:120]
    return render(request, 'obras/planejamento.html', {
        'form': form, 'metas': metas, 'pode_editar': request.user.is_staff
    })


@login_required(login_url='login_sistema')
def cadastros(request):
    """Cadastro aditivo, sem exclusão de dados e sem gerar obras fictícias."""
    if not request.user.is_staff:
        raise PermissionDenied('Cadastros de obras exigem conta autorizada.')
    torre_form = TorreForm()
    apartamento_form = ApartamentoForm()
    medicao_form = MedicaoMensalForm(
        initial={'mes_referencia': timezone.localdate().strftime('%Y-%m')}
    )
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'torre':
            torre_form = TorreForm(request.POST)
            if torre_form.is_valid():
                torre = torre_form.save()
                messages.success(request, f'Torre {torre.nome} cadastrada.')
                return redirect('cadastros')
        elif acao == 'apartamento':
            apartamento_form = ApartamentoForm(request.POST)
            if apartamento_form.is_valid():
                apartamento = apartamento_form.save()
                messages.success(request, f'Apartamento {apartamento.numero} cadastrado.')
                return redirect('cadastros')
        elif acao == 'medicao':
            medicao_form = MedicaoMensalForm(request.POST)
            if medicao_form.is_valid():
                with transaction.atomic():
                    medicao = medicao_form.save(commit=False)
                    medicao.status_iso = 'PENDENTE'
                    medicao.laudo_ia = 'Medição inicial cadastrada manualmente; sem laudo de IA.'
                    medicao.full_clean()
                    medicao.save()
                    HistoricoMedicao.objects.create(
                        medicao=medicao, autor=request.user, origem='MANUAL',
                        percentual_anterior=0,
                        percentual_novo=medicao.percentual_concluido,
                        status_anterior='', status_novo=medicao.status_iso,
                        etapa_anterior='', etapa_nova=medicao.etapa_atual,
                        observacao='Criação da medição mensal por usuário autorizado.',
                    )
                messages.success(
                    request, f'Medição de {medicao.mes_referencia} cadastrada, com FVS pendente.'
                )
                return redirect('cadastros')
        else:
            messages.error(request, 'Ação de cadastro desconhecida.')
    return render(request, 'obras/cadastros.html', {
        'torre_form': torre_form, 'apartamento_form': apartamento_form,
        'medicao_form': medicao_form,
        'torres': Torre.objects.all().order_by('nome'),
        'apartamentos': Apartamento.objects.select_related('torre')[:20],
        'medicoes': MedicaoMensal.objects.select_related(
            'apartamento__torre'
        ).order_by('-mes_referencia', '-id')[:20],
    }, status=400 if request.method == 'POST' else 200)
