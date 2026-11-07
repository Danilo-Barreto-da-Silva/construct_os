from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

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
