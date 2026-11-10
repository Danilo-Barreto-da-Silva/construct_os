"""Páginas seguras de projetos, QR Code e revisão de vistoria multimodal."""
import hashlib
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .forms_inteligentes import (
    TipologiaForm, AmbienteForm, ServicoTipoForm, CriterioForm, UnidadeForm,
    PesoUnidadeForm, DocumentoProjetoForm, ItemEsperadoForm, VideoVistoriaForm,
    MedicaoVerificadaForm,
)
from .models import (
    TipologiaUnidade, AmbienteTipologia, ServicoTipologia, CriterioVistoria,
    UnidadeInteligente, PesoServicoUnidade, DocumentoProjeto, ItemEsperadoProjeto,
    VistoriaInteligente, SugestaoEtapaIA, EventoMedicaoCriterio, Apartamento,
)
from .parametros import progresso_unidade, validar_medicao
from .modelos_inteligentes import validar_mes_referencia


def apenas_gestor(usuario):
    if not usuario.is_staff:
        raise PermissionDenied('Somente a equipe autorizada altera parâmetros de projeto.')


def pode_ver_video(usuario, visto):
    """Usuário de campo só vê sua própria gravação; gestor revisa todas."""
    if not (usuario.is_staff or visto.enviado_por_id == usuario.pk):
        raise PermissionDenied('Você não tem permissão para consultar esta vistoria.')


@login_required(login_url='login_sistema')
def catalogo_inteligente(request):
    tipologias = TipologiaUnidade.objects.select_related('torre').order_by('torre__nome','codigo')
    tid = request.GET.get('tipo','')
    tipologia = tipologias.filter(pk=int(tid)).first() if tid.isdecimal() else tipologias.first()
    formularios = {
        'tipologia': TipologiaForm(),
        'ambiente': AmbienteForm(initial={'tipologia': tipologia}),
        'servico': ServicoTipoForm(initial={'tipologia': tipologia}),
        'criterio': CriterioForm(tipologia=tipologia),
        'unidade': UnidadeForm(tipologia=tipologia, initial={'tipologia':tipologia}),
        'documento': DocumentoProjetoForm(initial={'tipologia': tipologia}),
        'item_projeto': ItemEsperadoForm(tipologia=tipologia),
    }
    if request.method == 'POST':
        apenas_gestor(request.user)
        acao = request.POST.get('acao','')
        if acao not in formularios:
            messages.error(request,'Operação de cadastro desconhecida.')
            return redirect('catalogo_inteligente')
        classe = type(formularios[acao])
        if acao in ('criterio','item_projeto','unidade'):
            formulario = classe(request.POST, request.FILES or None, tipologia=tipologia)
        else:
            formulario = classe(request.POST, request.FILES or None)
        formularios[acao] = formulario
        if formulario.is_valid():
            obj = formulario.save(commit=False)
            try:
                with transaction.atomic():
                    if acao == 'documento':
                        pdf = formulario.cleaned_data['arquivo']
                        pdf.seek(0)
                        obj.sha256 = hashlib.sha256(pdf.read()).hexdigest()
                        pdf.seek(0)
                        obj.enviado_por = request.user
                    obj.full_clean()
                    obj.save()
            except ValidationError as exc:
                formulario.add_error(None, exc)
            else:
                messages.success(request, 'Cadastro salvo. Revise os pesos e os itens do projeto antes de utilizar em medições.')
                ref = obj if acao == 'tipologia' else (
                    obj.tipologia if hasattr(obj,'tipologia') else (
                    obj.servico.tipologia if hasattr(obj,'servico') else (
                    obj.criterio.servico.tipologia if hasattr(obj,'criterio') else tipologia
                    ))
                )
                return redirect(reverse('catalogo_inteligente') + f'?tipo={ref.pk}')
    servicos = list(ServicoTipologia.objects.filter(tipologia=tipologia).prefetch_related(
        'criterios','criterios__ambiente',
    )) if tipologia else []
    total_pesos = sum((x.peso for x in servicos), 0)
    unidades = UnidadeInteligente.objects.filter(tipologia=tipologia).select_related('apartamento') if tipologia else []
    documentos = DocumentoProjeto.objects.filter(tipologia=tipologia) if tipologia else []
    itens = ItemEsperadoProjeto.objects.filter(documento__tipologia=tipologia).select_related(
        'criterio','documento'
    ) if tipologia else []
    return render(request, 'obras/catalogo_inteligente.html', {
        'tipologias':tipologias,'tipologia':tipologia,'formularios':formularios,
        'servicos':servicos,'total_pesos':total_pesos,'unidades':unidades,
        'documentos':documentos,'itens':itens,'pode_editar':request.user.is_staff,
    })


@login_required(login_url='login_sistema')
@require_POST
def conferir_item_projeto(request, item_id):
    apenas_gestor(request.user)
    item = get_object_or_404(ItemEsperadoProjeto,pk=item_id)
    item.conferido = True
    item.conferido_por = request.user
    item.save(update_fields=['conferido','conferido_por'])
    messages.success(request, 'Item do projeto conferido. A conferência não equivale à execução da obra.')
    return redirect(reverse('catalogo_inteligente') + f'?tipo={item.documento.tipologia_id}')


@login_required(login_url='login_sistema')
@require_POST
def salvar_peso_unidade(request, apartamento_id):
    apenas_gestor(request.user)
    cfg = get_object_or_404(UnidadeInteligente, apartamento_id=apartamento_id,ativo=True)
    sid = request.POST.get('servico','')
    original = (
        PesoServicoUnidade.objects.filter(unidade=cfg,servico_id=int(sid)).first()
        if sid.isdecimal() else None
    )
    form = PesoUnidadeForm(request.POST,instance=original,unidade=cfg)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.unidade = cfg
        try:
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            messages.error(request,str(exc))
        else:
            messages.success(request,'Peso personalizado salvo. Cadastre todos os serviços até somar exatamente 100%.')
    else:
        messages.error(request,form.errors.as_text()[:400])
    return redirect('unidade_inteligente',apartamento_id=apartamento_id)


@login_required(login_url='login_sistema')
def unidade_inteligente(request, apartamento_id):
    cfg = get_object_or_404(
        UnidadeInteligente.objects.select_related('apartamento__torre','tipologia'),
        apartamento_id=apartamento_id, ativo=True
    )
    mes = request.GET.get('mes',timezone.localdate().strftime('%Y-%m'))
    try:
        progresso = progresso_unidade(cfg,mes)
    except ValidationError:
        mes = timezone.localdate().strftime('%Y-%m')
        progresso = progresso_unidade(cfg,mes)
    criterios = CriterioVistoria.objects.filter(servico__tipologia=cfg.tipologia).select_related(
        'servico','ambiente'
    )
    personalizacoes = {
        p.servico_id:p.peso for p in cfg.pesos_proprios.all()
    }
    formulario = MedicaoVerificadaForm(unidade=cfg,initial={'mes':mes})
    formulario_peso = PesoUnidadeForm(unidade=cfg)
    lista_vistorias = cfg.apartamento.vistorias_inteligentes.select_related('enviado_por')
    if not request.user.is_staff:
        lista_vistorias = lista_vistorias.filter(enviado_por=request.user)
    return render(request,'obras/unidade_inteligente.html',{
        'cfg':cfg,'mes':mes,'progresso':progresso,'criterios':criterios,
        'personalizacoes':personalizacoes,'formulario':formulario,
        'formulario_peso':formulario_peso,'pode_editar':request.user.is_staff,
        'vistorias':lista_vistorias[:20],
        'video_form':VideoVistoriaForm(),
        'historico_medicoes':EventoMedicaoCriterio.objects.filter(
            medicao__apartamento=cfg.apartamento,
            medicao__mes_referencia__lte=mes,
        ).select_related('medicao__criterio__servico','autor').order_by(
            '-registrado_em','-id'
        )[:50],
    })


@login_required(login_url='login_sistema')
def vistoria_por_qr(request, token):
    cfg = get_object_or_404(UnidadeInteligente,token_qr=token,ativo=True)
    return redirect('unidade_inteligente',apartamento_id=cfg.apartamento_id)


@login_required(login_url='login_sistema')
@never_cache
def imagem_qr(request,apartamento_id):
    cfg = get_object_or_404(UnidadeInteligente,apartamento_id=apartamento_id,ativo=True)
    from qrcode import make
    from qrcode.image.svg import SvgPathImage
    uri = request.build_absolute_uri(reverse('vistoria_por_qr',kwargs={'token':cfg.token_qr}))
    saida = BytesIO()
    make(uri, image_factory=SvgPathImage, box_size=8, border=3).save(saida)
    resp = HttpResponse(saida.getvalue(),content_type='image/svg+xml')
    resp['Cache-Control'] = 'private, no-store'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


@login_required(login_url='login_sistema')
@require_POST
def enviar_video_inteligente(request,apartamento_id):
    cfg = get_object_or_404(UnidadeInteligente,apartamento_id=apartamento_id,ativo=True)
    # Limite simples por conta e unidade; produção exige também rate limiting
    # reverso, quotas de armazenamento e antivírus nos uploads.
    desde = timezone.now() - timedelta(hours=24)
    if (VistoriaInteligente.objects.filter(enviado_por=request.user,criado_em__gte=desde).count() >= 12
        or VistoriaInteligente.objects.filter(apartamento=cfg.apartamento,criado_em__gte=desde).count() >= 20):
        messages.error(request,'Limite diário de gravações alcançado. Aguarde antes de enviar outro vídeo.')
        return redirect('unidade_inteligente',apartamento_id=apartamento_id)
    form = VideoVistoriaForm(request.POST,request.FILES)
    if not form.is_valid():
        messages.error(request,'Vídeo não enviado: ' + form.errors.as_text()[:400])
        return redirect('unidade_inteligente',apartamento_id=apartamento_id)
    visto = VistoriaInteligente.objects.create(
        apartamento=cfg.apartamento,enviado_por=request.user,
        arquivo=form.cleaned_data['arquivo'],
        observacao=form.cleaned_data['observacao'],
        estado='PENDENTE',
    )
    messages.success(request,'Vídeo armazenado de forma privada. A análise com IA depende de configuração e processamento separado.')
    return redirect('detalhe_vistoria_inteligente',vistoria_id=visto.pk)


@login_required(login_url='login_sistema')
@require_POST
def validar_criterio_view(request,apartamento_id):
    apenas_gestor(request.user)
    cfg = get_object_or_404(UnidadeInteligente,apartamento_id=apartamento_id,ativo=True)
    form = MedicaoVerificadaForm(request.POST,unidade=cfg)
    if form.is_valid():
        d = form.cleaned_data
        try:
            _, mudou = validar_medicao(
                autor=request.user,unidade=cfg,criterio=d['criterio'],
                mes=d['mes'],percentual=d['percentual'],
                observacao=d['observacao'],vistoria=d['vistoria'],
            )
        except ValidationError as exc:
            messages.error(request,'Medição rejeitada: '+str(exc))
        else:
            messages.success(request, 'Subetapa verificada e auditada.' if mudou else 'Percentual já estava registrado.')
        return redirect(reverse('unidade_inteligente',args=[apartamento_id]) + f'?mes={d["mes"]}')
    messages.error(request,'Medição inválida: '+form.errors.as_text()[:450])
    return redirect('unidade_inteligente',apartamento_id=apartamento_id)


@login_required(login_url='login_sistema')
def detalhe_vistoria_inteligente(request,vistoria_id):
    visto = get_object_or_404(
        VistoriaInteligente.objects.select_related('apartamento__torre','enviado_por'),
        pk=vistoria_id
    )
    pode_ver_video(request.user, visto)
    cfg = get_object_or_404(UnidadeInteligente,apartamento=visto.apartamento,ativo=True)
    sugestoes = list(visto.sugestoes.select_related(
        'criterio__servico','revisado_por'
    ))
    # Relatorios anteriores foram salvos com barras-n literais.
    # Normalizar apenas na exibicao preserva o registro original auditavel.
    for sugestao in sugestoes:
        sugestao.justificativa_exibida = sugestao.justificativa.replace('\\n', '\n')
    return render(request,'obras/detalhe_vistoria_inteligente.html',{
        'visto':visto,'cfg':cfg,'sugestoes':sugestoes,
        'pode_editar':request.user.is_staff,
    })


@login_required(login_url='login_sistema')
@never_cache
def video_privado(request,vistoria_id):
    visto = get_object_or_404(VistoriaInteligente,pk=vistoria_id)
    pode_ver_video(request.user, visto)
    try:
        arquivo = visto.arquivo.open('rb')
    except OSError:
        raise Http404('Arquivo indisponível.')
    resp = FileResponse(arquivo,as_attachment=True,filename=f'vistoria-{visto.pk}.webm')
    resp['Cache-Control']='private, no-store'
    resp['X-Content-Type-Options']='nosniff'
    return resp


@login_required(login_url='login_sistema')
@never_cache
def documento_privado(request,documento_id):
    apenas_gestor(request.user)
    doc = get_object_or_404(DocumentoProjeto,pk=documento_id)
    try:
        arquivo = doc.arquivo.open('rb')
    except OSError:
        raise Http404('Documento indisponível.')
    resp = FileResponse(arquivo,as_attachment=True,filename=f'projeto-{doc.pk}.pdf')
    resp['Cache-Control']='private, no-store'
    resp['X-Content-Type-Options']='nosniff'
    return resp



@login_required(login_url='login_sistema')
@require_POST
def reprocessar_vistoria(request,vistoria_id):
    apenas_gestor(request.user)
    visto = get_object_or_404(VistoriaInteligente,pk=vistoria_id)
    if visto.estado != 'ERRO' or visto.sugestoes.exists():
        messages.error(request,'Somente análises que falharam e não têm sugestões podem ser reprocessadas.')
    else:
        visto.estado='PENDENTE'
        visto.erro_publico=''
        visto.save(update_fields=['estado','erro_publico'])
        messages.success(request,'Vídeo recolocado na fila para análise por comando.')
    return redirect('detalhe_vistoria_inteligente',vistoria_id=vistoria_id)



@login_required(login_url='login_sistema')
@never_cache
def etiquetas_tipologia(request,tipologia_id):
    """Folha para impressão dos QR Codes; não expõe documentos ou dados sem login."""
    apenas_gestor(request.user)
    tipo=get_object_or_404(
        TipologiaUnidade.objects.select_related('torre'),pk=tipologia_id
    )
    unidades=UnidadeInteligente.objects.filter(tipologia=tipo,ativo=True).select_related(
        'apartamento'
    ).order_by('apartamento__andar','apartamento__numero')
    return render(request,'obras/etiquetas_tipologia.html',{
        'tipo':tipo,'unidades':unidades,
    })



@login_required(login_url='login_sistema')
def comparar_vistoria_projeto(request,vistoria_id):
    """Visualização LADO A LADO para conferência humana; não é sobreposição BIM."""
    apenas_gestor(request.user)
    visto=get_object_or_404(
        VistoriaInteligente.objects.select_related('apartamento__torre'),pk=vistoria_id
    )
    cfg=get_object_or_404(UnidadeInteligente,apartamento=visto.apartamento,ativo=True)
    docs=DocumentoProjeto.objects.filter(tipologia=cfg.tipologia).order_by('disciplina','-enviado_em')
    escolhido=request.GET.get('documento','')
    doc=docs.filter(pk=int(escolhido)).first() if escolhido.isdecimal() else docs.first()
    return render(request,'obras/comparar_vistoria_projeto.html',{
        'visto':visto,'cfg':cfg,'documentos':docs,'documento':doc,
        'itens':ItemEsperadoProjeto.objects.filter(documento=doc).select_related(
            'criterio','conferido_por'
        ) if doc else [],
    })


@login_required(login_url='login_sistema')
@never_cache
def video_reproducao(request,vistoria_id):
    visto=get_object_or_404(VistoriaInteligente,pk=vistoria_id)
    pode_ver_video(request.user, visto)
    try:
        arquivo=visto.arquivo.open('rb')
    except OSError:
        raise Http404('Arquivo indisponível.')
    extensao=Path(visto.arquivo.name).suffix.lower()
    mime={'.mp4':'video/mp4','.mov':'video/quicktime','.webm':'video/webm'}.get(
        extensao,'application/octet-stream'
    )
    resposta=FileResponse(arquivo,content_type=mime)
    resposta['Content-Disposition']='inline'
    resposta['Cache-Control']='private, no-store'
    resposta['X-Content-Type-Options']='nosniff'
    return resposta


@login_required(login_url='login_sistema')
@never_cache
@xframe_options_sameorigin
def documento_visualizacao(request,documento_id):
    apenas_gestor(request.user)
    doc=get_object_or_404(DocumentoProjeto,pk=documento_id)
    try:
        arquivo=doc.arquivo.open('rb')
    except OSError:
        raise Http404('Documento indisponível.')
    resposta=FileResponse(arquivo,content_type='application/pdf')
    resposta['Content-Disposition']='inline'
    resposta['Cache-Control']='private, no-store'
    resposta['X-Content-Type-Options']='nosniff'
    return resposta


@login_required(login_url='login_sistema')
@never_cache
def comparar_unidades_tipologia(request, tipologia_id):
    """Compara vistorias de salas da MESMA tipologia, sem inferir avanço de imagens parciais."""
    apenas_gestor(request.user)
    tipo = get_object_or_404(
        TipologiaUnidade.objects.select_related('torre'), pk=tipologia_id
    )
    mes = request.GET.get('mes', timezone.localdate().strftime('%Y-%m'))
    try:
        validar_mes_referencia(mes)
    except ValidationError:
        mes = timezone.localdate().strftime('%Y-%m')

    unidades = UnidadeInteligente.objects.filter(
        tipologia=tipo, ativo=True
    ).select_related('apartamento__torre').order_by(
        'apartamento__andar','apartamento__numero'
    )[:25]
    comparativos = []
    for cfg in unidades:
        registro = cfg.apartamento.vistorias_inteligentes.select_related(
            'enviado_por'
        ).prefetch_related(
            'sugestoes__criterio__servico'
        ).order_by('-criado_em','-pk').first()
        sugestoes = list(registro.sugestoes.all()) if registro else []
        comparativos.append({
            'cfg': cfg,
            'vistoria': registro,
            'sugestoes': sugestoes,
            'resumo': progresso_unidade(cfg, mes),
            'visuais': sum(s.fonte in ('VISUAL', 'AMBAS') for s in sugestoes),
            'audio': sum(s.fonte == 'AUDIO' for s in sugestoes),
            'incertos': sum(s.fonte == 'INCERTO' for s in sugestoes),
        })
    return render(request, 'obras/comparar_unidades_tipologia.html', {
        'tipo': tipo,
        'mes': mes,
        'comparativos': comparativos,
    })
