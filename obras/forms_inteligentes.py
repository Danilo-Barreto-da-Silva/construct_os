"""Formulários operacionais da medição parametrizada."""
from django import forms
from django.core.exceptions import ValidationError
from .forms import StyledModelForm
from .models import (
    TipologiaUnidade, AmbienteTipologia, ServicoTipologia, CriterioVistoria,
    UnidadeInteligente, PesoServicoUnidade, DocumentoProjeto, ItemEsperadoProjeto,
)


class TipologiaForm(StyledModelForm):
    class Meta:
        model = TipologiaUnidade
        fields = ['torre','codigo','nome','descricao']
        widgets = {'descricao': forms.Textarea(attrs={'rows':2})}


class AmbienteForm(StyledModelForm):
    class Meta:
        model = AmbienteTipologia
        fields = ['tipologia','codigo','nome','area_m2']


class ServicoTipoForm(StyledModelForm):
    class Meta:
        model = ServicoTipologia
        fields = ['tipologia','codigo','nome','peso']
        widgets = {'peso': forms.NumberInput(attrs={'step':'0.01','min':'0.01','max':'100'})}


class CriterioForm(StyledModelForm):
    class Meta:
        model = CriterioVistoria
        fields = ['servico','ambiente','codigo','descricao','peso','metodo','orientacao']
        widgets = {'peso': forms.NumberInput(attrs={'step':'0.01','min':'0.01','max':'100'}),
                   'orientacao': forms.Textarea(attrs={'rows':2})}

    def __init__(self,*args,tipologia=None,**kwargs):
        super().__init__(*args,**kwargs)
        if tipologia:
            self.fields['servico'].queryset = ServicoTipologia.objects.filter(tipologia=tipologia)
            self.fields['ambiente'].queryset = AmbienteTipologia.objects.filter(tipologia=tipologia)


class UnidadeForm(StyledModelForm):
    class Meta:
        model = UnidadeInteligente
        fields = ['apartamento','tipologia','ativo']

    def __init__(self,*args,tipologia=None,**kwargs):
        super().__init__(*args,**kwargs)
        if tipologia:
            self.fields['apartamento'].queryset = self.fields['apartamento'].queryset.filter(
                torre=tipologia.torre
            )
            self.fields['tipologia'].queryset = self.fields['tipologia'].queryset.filter(
                torre=tipologia.torre
            )


class PesoUnidadeForm(StyledModelForm):
    class Meta:
        model = PesoServicoUnidade
        fields = ['servico','peso']
        widgets = {'peso': forms.NumberInput(attrs={'step':'0.01','min':'0.01','max':'100'})}

    def __init__(self,*args,unidade=None,**kwargs):
        super().__init__(*args,**kwargs)
        if unidade:
            self.fields['servico'].queryset = ServicoTipologia.objects.filter(tipologia=unidade.tipologia)


class DocumentoProjetoForm(StyledModelForm):
    class Meta:
        model = DocumentoProjeto
        fields = ['tipologia','disciplina','nome','revisao','arquivo']

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        if arquivo.size > 15 * 1024 * 1024:
            raise ValidationError('PDF acima do limite de 15 MB.')
        inicio = arquivo.read(5)
        arquivo.seek(0)
        if inicio != b'%PDF-':
            raise ValidationError('Envie apenas um arquivo PDF válido.')
        return arquivo


class ItemEsperadoForm(StyledModelForm):
    class Meta:
        model = ItemEsperadoProjeto
        fields = ['documento','criterio','pagina','referencia','descricao','quantidade','unidade_medida']
        widgets = {'descricao': forms.Textarea(attrs={'rows':2})}

    def __init__(self,*args,tipologia=None,**kwargs):
        super().__init__(*args,**kwargs)
        if tipologia:
            self.fields['documento'].queryset = DocumentoProjeto.objects.filter(tipologia=tipologia)
            self.fields['criterio'].queryset = CriterioVistoria.objects.filter(servico__tipologia=tipologia)


class VideoVistoriaForm(forms.Form):
    arquivo = forms.FileField(label='Gravação (vídeo com áudio, quando disponível)')
    observacao = forms.CharField(
        label='Narração/observação adicional',
        required=False,max_length=2000,
        widget=forms.Textarea(attrs={'rows':3}),
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        if arquivo.size > 30*1024*1024:
            raise ValidationError('O vídeo excede o limite de 30 MB. Envie uma gravação mais curta.')
        if arquivo.size < 20:
            raise ValidationError('Arquivo de vídeo vazio ou inválido.')
        inicio = arquivo.read(16)
        arquivo.seek(0)
        # Detecta contêiner, sem confiar em extensão ou MIME declarados.
        if not (inicio[4:8] == b'ftyp' or inicio[:4] == b'\x1a\x45\xdf\xa3'):
            raise ValidationError('Envie vídeo MP4, MOV ou WebM compatível.')
        return arquivo


class MedicaoVerificadaForm(forms.Form):
    criterio = forms.ModelChoiceField(queryset=CriterioVistoria.objects.none(),label='Critério')
    mes = forms.CharField(label='Mês da medição',widget=forms.TextInput(attrs={'type':'month'}))
    percentual = forms.DecimalField(label='Percentual confirmado da subetapa',
        min_value=0,max_value=100,max_digits=5,decimal_places=2,
        widget=forms.NumberInput(attrs={'min':0,'max':100,'step':0.01}))
    observacao = forms.CharField(label='Observação técnica',required=False,max_length=500,
        widget=forms.Textarea(attrs={'rows':2}))
    vistoria = forms.ModelChoiceField(queryset=None,required=False,label='Vídeo de origem')

    def __init__(self,*args,unidade,**kwargs):
        super().__init__(*args,**kwargs)
        from .models import VistoriaInteligente
        self.fields['criterio'].queryset = CriterioVistoria.objects.filter(
            servico__tipologia=unidade.tipologia
        ).select_related('servico')
        self.fields['vistoria'].queryset = VistoriaInteligente.objects.filter(
            apartamento=unidade.apartamento
        )
