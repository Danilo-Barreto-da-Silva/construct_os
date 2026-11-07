from django.db import models

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
        ('PENDENTE', 'Pendente de FVS (Trava 90%)'),
        ('NAO_CONFORME', 'Não Conforme (RNC Aberta)'),
    ]

    apartamento = models.ForeignKey(Apartamento, related_name='medicoes', on_delete=models.CASCADE)
    mes_referencia = models.CharField(max_length=7, default='2026-11')
    etapa_atual = models.CharField(max_length=100, default='Alvenaria e Instalações')
    percentual_concluido = models.IntegerField(default=0)
    requisito_iso = models.CharField(max_length=80, default='ISO 9001 (8.5.1) / FVS-03')
    status_iso = models.CharField(max_length=20, choices=STATUS_ISO, default='PENDENTE')
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
        trava_acionada = False
        if self.percentual_concluido >= 100 and self.status_iso != 'CONFORME':
            self.percentual_concluido = 90
            trava_acionada = True
        self.save()
        return trava_acionada