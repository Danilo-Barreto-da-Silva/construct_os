"""Modelagem da vistoria por apartamento e comparação com projeto.

A evidência de IA é sempre uma sugestão. Aprovação de FVS e medições mensais
existentes ficam intocadas até revisão técnica em fluxo separado.
"""
import uuid
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from .models import Apartamento, Torre, MedicaoMensal, validar_mes_referencia


def arquivo_privado(instance, filename):
    ext = Path(filename).suffix.lower()
    if ext not in ('.mp4', '.mov', '.webm', '.pdf'):
        ext = '.bin'
    return f'privado_vistorias/{uuid.uuid4().hex}{ext}'


class TipologiaUnidade(models.Model):
    torre = models.ForeignKey(Torre, on_delete=models.PROTECT, related_name='tipologias')
    codigo = models.CharField(max_length=30)
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['torre__nome', 'codigo']
        constraints = [models.UniqueConstraint(fields=['torre', 'codigo'], name='tipologia_unica_torre')]

    def __str__(self):
        return f'{self.torre.nome} · {self.codigo} — {self.nome}'


class AmbienteTipologia(models.Model):
    tipologia = models.ForeignKey(TipologiaUnidade, on_delete=models.PROTECT, related_name='ambientes')
    codigo = models.CharField(max_length=30)
    nome = models.CharField(max_length=100)
    area_m2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                  validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        ordering = ['tipologia_id', 'codigo']
        constraints = [models.UniqueConstraint(fields=['tipologia', 'codigo'], name='ambiente_unico_tipologia')]

    def __str__(self):
        return f'{self.codigo} — {self.nome}'


class ServicoTipologia(models.Model):
    tipologia = models.ForeignKey(TipologiaUnidade, on_delete=models.PROTECT, related_name='servicos')
    codigo = models.CharField(max_length=30)
    nome = models.CharField(max_length=120)
    peso = models.DecimalField(max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])

    class Meta:
        ordering = ['tipologia_id', 'codigo']
        constraints = [models.UniqueConstraint(fields=['tipologia', 'codigo'], name='servico_unico_tipologia')]

    def clean(self):
        super().clean()
        if self.tipologia_id and self.peso is not None:
            outros = ServicoTipologia.objects.filter(tipologia_id=self.tipologia_id).exclude(pk=self.pk)
            peso = sum((x.peso for x in outros), Decimal('0')) + self.peso
            if peso > Decimal('100'):
                raise ValidationError({'peso': 'A soma dos serviços da tipologia não pode ultrapassar 100%.'})
            # Bloqueia reponderação indireta de medições já verificadas.
            if MedicaoCriterio.objects.filter(criterio__servico__tipologia_id=self.tipologia_id).exists():
                anterior = ServicoTipologia.objects.filter(pk=self.pk).first() if self.pk else None
                if (anterior is None or anterior.peso != self.peso or
                        anterior.tipologia_id != self.tipologia_id):
                    raise ValidationError(
                        'Serviços e pesos ficam congelados após a primeira medição verificada. '
                        'Crie uma nova versão de tipologia para mudar a metodologia.'
                    )

    def __str__(self):
        return f'{self.codigo} · {self.nome} ({self.peso}%)'


class CriterioVistoria(models.Model):
    MODOS = [
        ('VISUAL', 'Inspeção visual'),
        ('TESTE', 'Ensaio ou teste técnico'),
        ('MEDICAO', 'Medição instrumental'),
        ('DOCUMENTAL', 'Comprovação documental'),
    ]
    servico = models.ForeignKey(ServicoTipologia, on_delete=models.PROTECT, related_name='criterios')
    ambiente = models.ForeignKey(AmbienteTipologia, on_delete=models.PROTECT, related_name='criterios', null=True, blank=True)
    codigo = models.CharField(max_length=40)
    descricao = models.CharField(max_length=220)
    peso = models.DecimalField(max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])
    metodo = models.CharField(max_length=12, choices=MODOS, default='VISUAL')
    orientacao = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['servico_id', 'codigo']
        constraints = [models.UniqueConstraint(fields=['servico', 'codigo'], name='criterio_unico_servico')]

    def clean(self):
        super().clean()
        if self.ambiente_id and self.servico_id and self.ambiente.tipologia_id != self.servico.tipologia_id:
            raise ValidationError('Ambiente e serviço precisam pertencer à mesma tipologia.')
        if self.servico_id and self.peso is not None:
            outros = CriterioVistoria.objects.filter(servico_id=self.servico_id).exclude(pk=self.pk)
            if sum((x.peso for x in outros), Decimal('0')) + self.peso > 100:
                raise ValidationError({'peso': 'Os pesos dos critérios deste serviço ultrapassam 100%.'})
            if MedicaoCriterio.objects.filter(criterio__servico__tipologia_id=self.servico.tipologia_id).exists():
                anterior = CriterioVistoria.objects.filter(pk=self.pk).first() if self.pk else None
                if (anterior is None or anterior.peso != self.peso or
                        anterior.servico_id != self.servico_id or
                        anterior.ambiente_id != self.ambiente_id):
                    raise ValidationError(
                        'Não altere os critérios, ambientes ou pesos de uma tipologia com '
                        'medições validadas. Crie uma nova versão.'
                    )

    def __str__(self):
        return f'{self.servico.codigo} / {self.codigo} — {self.descricao}'


class UnidadeInteligente(models.Model):
    apartamento = models.OneToOneField(Apartamento, on_delete=models.PROTECT, related_name='config_inteligente')
    tipologia = models.ForeignKey(TipologiaUnidade, on_delete=models.PROTECT, related_name='unidades')
    token_qr = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.apartamento_id and self.tipologia_id and self.apartamento.torre_id != self.tipologia.torre_id:
            raise ValidationError('A tipologia deve pertencer à mesma torre do apartamento.')
        if self.pk:
            anterior = UnidadeInteligente.objects.filter(pk=self.pk).first()
            if anterior and anterior.tipologia_id != self.tipologia_id:
                if MedicaoCriterio.objects.filter(apartamento_id=self.apartamento_id).exists():
                    raise ValidationError('Não altere a tipologia após registrar medições verificadas.')

    def __str__(self):
        return f'{self.apartamento} / {self.tipologia.codigo}'


class PesoServicoUnidade(models.Model):
    """Personalização opcional: para ser válida, deve cobrir TODOS os serviços e somar 100%."""
    unidade = models.ForeignKey(UnidadeInteligente, on_delete=models.PROTECT, related_name='pesos_proprios')
    servico = models.ForeignKey(ServicoTipologia, on_delete=models.PROTECT, related_name='pesos_unidades')
    peso = models.DecimalField(max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['unidade', 'servico'], name='peso_unico_unidade_servico')]

    def clean(self):
        super().clean()
        if self.unidade_id and self.servico_id:
            if self.unidade.tipologia_id != self.servico.tipologia_id:
                raise ValidationError('O serviço não pertence à tipologia do apartamento.')
            outros = PesoServicoUnidade.objects.filter(unidade_id=self.unidade_id).exclude(pk=self.pk)
            if self.peso is not None and sum((x.peso for x in outros), Decimal('0')) + self.peso > 100:
                raise ValidationError({'peso': 'Pesos próprios ultrapassam 100%.'})
            if MedicaoCriterio.objects.filter(apartamento_id=self.unidade.apartamento_id).exists():
                anterior = PesoServicoUnidade.objects.filter(pk=self.pk).first() if self.pk else None
                if (anterior is None or anterior.peso != self.peso or
                        anterior.servico_id != self.servico_id or anterior.unidade_id != self.unidade_id):
                    raise ValidationError(
                        'Não crie nem altere pesos individuais após medições verificadas. '
                        'Uma nova versão de metodologia deve ser configurada separadamente.'
                    )


class DocumentoProjeto(models.Model):
    DISCIPLINAS = [('ARQ','Arquitetônico'), ('ELE','Elétrico'), ('AGUA','Água'), ('ESG','Esgoto'),
                   ('EST','Estrutural'), ('OUT','Outros')]
    tipologia = models.ForeignKey(TipologiaUnidade, on_delete=models.PROTECT, related_name='documentos')
    disciplina = models.CharField(max_length=5, choices=DISCIPLINAS)
    nome = models.CharField(max_length=150)
    revisao = models.CharField(max_length=40, blank=True, default='')
    arquivo = models.FileField(upload_to=arquivo_privado)
    sha256 = models.CharField(max_length=64, blank=True, default='')
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enviado_em', '-id']


class ItemEsperadoProjeto(models.Model):
    """Dados do desenho só viram requisito após conferência humana."""
    documento = models.ForeignKey(DocumentoProjeto, on_delete=models.PROTECT, related_name='itens_esperados')
    criterio = models.ForeignKey(CriterioVistoria, on_delete=models.PROTECT, related_name='itens_projeto')
    pagina = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    referencia = models.CharField(max_length=120)
    descricao = models.TextField(max_length=1000)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(0)])
    unidade_medida = models.CharField(max_length=20, blank=True, default='')
    conferido = models.BooleanField(default=False)
    conferido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='itens_projeto_conferidos')

    def clean(self):
        super().clean()
        if self.documento_id and self.criterio_id:
            if self.documento.tipologia_id != self.criterio.servico.tipologia_id:
                raise ValidationError('Documento e critério precisam ser da mesma tipologia.')


class VistoriaInteligente(models.Model):
    SITUACOES = [('PENDENTE','Aguardando análise'), ('PROCESSANDO','Processando'),
                 ('ANALISADA','Sugestões disponíveis'), ('ERRO','Erro de processamento')]
    apartamento = models.ForeignKey(Apartamento, on_delete=models.PROTECT, related_name='vistorias_inteligentes')
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    arquivo = models.FileField(upload_to=arquivo_privado)
    observacao = models.TextField(max_length=2000, blank=True, default='')
    estado = models.CharField(max_length=12, choices=SITUACOES, default='PENDENTE')
    criado_em = models.DateTimeField(auto_now_add=True)
    processado_em = models.DateTimeField(null=True, blank=True)
    modelo = models.CharField(max_length=80, blank=True, default='')
    transcricao_ia = models.TextField(blank=True, default='')
    resumo_ia = models.TextField(blank=True, default='')
    erro_publico = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        ordering = ['-criado_em', '-id']


class SugestaoEtapaIA(models.Model):
    FONTES = [('VISUAL','Evidência visual'), ('AUDIO','Declaração do áudio'),
              ('AMBAS','Áudio e vídeo'), ('INCERTO','Não verificável')]
    vistoria = models.ForeignKey(VistoriaInteligente, on_delete=models.PROTECT, related_name='sugestoes')
    criterio = models.ForeignKey(CriterioVistoria, on_delete=models.PROTECT, related_name='sugestoes')
    fonte = models.CharField(max_length=8, choices=FONTES, default='INCERTO')
    percentual_sugerido = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                               validators=[MinValueValidator(0), MaxValueValidator(100)])
    instante_segundos = models.PositiveIntegerField(null=True, blank=True)
    justificativa = models.TextField(max_length=1500)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    revisado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['vistoria', 'criterio'], name='sugestao_unica_criterio_video')]

    def clean(self):
        super().clean()
        config = UnidadeInteligente.objects.filter(apartamento_id=self.vistoria.apartamento_id).first() if self.vistoria_id else None
        if config and self.criterio_id and self.criterio.servico.tipologia_id != config.tipologia_id:
            raise ValidationError('O critério não pertence à tipologia da unidade.')


class MedicaoCriterio(models.Model):
    """Medição validada por humano, NÃO altera MedicaoMensal/FVS automaticamente."""
    apartamento = models.ForeignKey(Apartamento, on_delete=models.PROTECT, related_name='medicoes_criterios')
    criterio = models.ForeignKey(CriterioVistoria, on_delete=models.PROTECT, related_name='medicoes')
    mes_referencia = models.CharField(max_length=7, validators=[validar_mes_referencia])
    percentual_validado = models.DecimalField(max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    vistoria_origem = models.ForeignKey(VistoriaInteligente, on_delete=models.PROTECT, null=True, blank=True)
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['apartamento','criterio','mes_referencia'],
                                                name='criterio_apto_mes_unico')]

    def clean(self):
        super().clean()
        if self.apartamento_id and self.criterio_id:
            cfg = UnidadeInteligente.objects.filter(apartamento_id=self.apartamento_id).first()
            if not cfg or self.criterio.servico.tipologia_id != cfg.tipologia_id:
                raise ValidationError('Critério incompatível com o apartamento.')
        if self.vistoria_origem_id and self.vistoria_origem.apartamento_id != self.apartamento_id:
            raise ValidationError('A vistoria pertence a outro apartamento.')


class EventoMedicaoCriterio(models.Model):
    medicao = models.ForeignKey(MedicaoCriterio, on_delete=models.PROTECT, related_name='eventos')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    registrado_em = models.DateTimeField(auto_now_add=True)
    anterior = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    novo = models.DecimalField(max_digits=5, decimal_places=2)
    observacao = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['-registrado_em', '-id']
