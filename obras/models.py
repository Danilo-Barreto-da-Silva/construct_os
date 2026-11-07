from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.core.exceptions import ValidationError
import re

class Torre(models.Model):
    nome = models.CharField(max_length=50)
    total_andares = models.IntegerField(default=6)

    def __str__(self):
        return self.nome

class Apartamento(models.Model):
    torre = models.ForeignKey(Torre, related_name='apartamentos', on_delete=models.CASCADE)
    andar = models.IntegerField()
    numero = models.CharField(max_length=10)

    class Meta:
        ordering = ['-andar', 'numero']

    def __str__(self):
        return f"{self.torre.nome} - Apto {self.numero}"

class MedicaoMensal(models.Model):
    STATUS_ISO = [
        ('CONFORME', 'Conforme (ISO 9001 OK)'),
        ('PENDENTE', 'Pendente de FVS'),
        ('NAO_CONFORME', 'Não Conforme (RNC Aberta)'),
    ]

    apartamento = models.ForeignKey(Apartamento, related_name='medicoes', on_delete=models.CASCADE)
    mes_referencia = models.CharField(max_length=7, default='2026-11')
    etapa_atual = models.CharField(max_length=100, default='Alvenaria e Instalações')
    percentual_concluido = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    requisito_iso = models.CharField(max_length=80, default='ISO 9001 (8.5.1) / FVS-03')
    status_iso = models.CharField(max_length=20, choices=STATUS_ISO, default='PENDENTE')
    sugestao_ia = models.TextField(blank=True, default='')
    fvs_aprovada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='fvs_aprovadas')
    fvs_aprovada_em = models.DateTimeField(null=True, blank=True)
    laudo_ia = models.TextField(blank=True, default='Aguardando envio de vídeo para diagnóstico.')
    video_vistoria = models.FileField(upload_to='videos_obra/', null=True, blank=True)

    def cor_status(self):
        if self.status_iso == 'NAO_CONFORME':
            return 'red'
        if self.percentual_concluido == 100 and self.status_iso == 'CONFORME':
            return 'green'
        if self.percentual_concluido >= 90 and self.status_iso != 'CONFORME':
            return 'yellow'
        return 'blue'

    def salvar_com_trava_iso(self):
        """Compatibilidade: qualidade não altera o avanço físico medido."""
        self.full_clean()
        self.save()
        return False

class HistoricoMedicao(models.Model):
    """Trilha de auditoria dos registros posteriores à implantação deste recurso."""
    medicao = models.ForeignKey(MedicaoMensal, related_name='historico', on_delete=models.PROTECT)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    registrado_em = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(max_length=20, choices=[('MANUAL', 'Atualização manual'), ('SUGESTAO_IA', 'Sugestão de IA')], default='MANUAL')
    percentual_anterior = models.IntegerField(default=0)
    percentual_novo = models.IntegerField(default=0)
    status_anterior = models.CharField(max_length=20, default='PENDENTE')
    status_novo = models.CharField(max_length=20, default='PENDENTE')
    etapa_anterior = models.CharField(max_length=100, blank=True, default='')
    etapa_nova = models.CharField(max_length=100, blank=True, default='')
    observacao = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-registrado_em', '-id']

    def __str__(self):
        return f'{self.medicao} - {self.get_origem_display()} em {self.registrado_em:%d/%m/%Y %H:%M}'


def validar_mes_referencia(value):
    """Mês civil no padrão AAAA-MM, sem aceitar valores inválidos."""
    if not re.fullmatch(r'20\\d{2}-(0[1-9]|1[0-2])', value or ''):
        raise ValidationError('Informe um mês entre 2000-01 e 2099-12 (AAAA-MM).')


class PlanejamentoMensal(models.Model):
    """Meta mensal por torre; não representa automaticamente uma Curva S ponderada."""
    torre = models.ForeignKey(Torre, related_name='planejamentos', on_delete=models.PROTECT)
    mes_referencia = models.CharField(max_length=7, validators=[validar_mes_referencia])
    percentual_planejado = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['mes_referencia', 'torre__nome']
        constraints = [
            models.UniqueConstraint(fields=['torre', 'mes_referencia'], name='planejamento_mes_torre_unico')
        ]

    def __str__(self):
        return f'{self.torre} • {self.mes_referencia}: {self.percentual_planejado}%'


class NaoConformidade(models.Model):
    PRIORIDADES = [
        ('BAIXA', 'Baixa'), ('MEDIA', 'Média'), ('ALTA', 'Alta'), ('CRITICA', 'Crítica'),
    ]
    SITUACOES = [
        ('ABERTA', 'Aberta'), ('TRATAMENTO', 'Em tratamento'), ('RESOLVIDA', 'Resolvida'),
    ]
    medicao = models.ForeignKey(
        MedicaoMensal, related_name='rncs', on_delete=models.PROTECT
    )
    titulo = models.CharField(max_length=140)
    descricao = models.TextField(max_length=3000)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADES, default='MEDIA')
    situacao = models.CharField(max_length=12, choices=SITUACOES, default='ABERTA')
    acao_corretiva = models.TextField(max_length=3000, blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rncs_atribuidas'
    )
    prazo = models.DateField(null=True, blank=True)
    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rncs_abertas'
    )
    aberta_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    encerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rncs_encerradas'
    )
    encerrada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-aberta_em', '-id']

    def clean(self):
        super().clean()
        if self.situacao == 'RESOLVIDA' and not (self.acao_corretiva or '').strip():
            raise ValidationError({'acao_corretiva': 'Informe a ação corretiva antes de encerrar a RNC.'})

    def __str__(self):
        return f'RNC #{self.pk} - {self.titulo}'


class EventoRNC(models.Model):
    rnc = models.ForeignKey(NaoConformidade, related_name='eventos', on_delete=models.PROTECT)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True)
    situacao_anterior = models.CharField(max_length=12, blank=True)
    situacao_nova = models.CharField(max_length=12)
    descricao = models.TextField()

    class Meta:
        ordering = ['-criado_em', '-id']


class ItemFVS(models.Model):
    RESULTADOS = [
        ('PENDENTE', 'Não verificado'),
        ('CONFORME', 'Conforme'),
        ('NAO_CONFORME', 'Não conforme'),
        ('NA', 'Não se aplica'),
    ]
    medicao = models.ForeignKey(
        MedicaoMensal, related_name='itens_fvs', on_delete=models.PROTECT
    )
    descricao = models.CharField(max_length=180)
    resultado = models.CharField(max_length=15, choices=RESULTADOS, default='PENDENTE')
    observacao = models.TextField(max_length=1000, blank=True)
    verificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.medicao} - {self.descricao}'


class EventoFVS(models.Model):
    item = models.ForeignKey(ItemFVS, related_name='eventos', on_delete=models.PROTECT)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    criado_em = models.DateTimeField(auto_now_add=True)
    resultado_anterior = models.CharField(max_length=15, blank=True)
    resultado_novo = models.CharField(max_length=15)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ['-criado_em', '-id']
