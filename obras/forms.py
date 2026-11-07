from django import forms
from django.contrib.auth import get_user_model

from .models import NaoConformidade, ItemFVS, PlanejamentoMensal


class StyledModelForm(forms.ModelForm):
    """Formulários de entrada com visual consistente e validação Django."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = (
                'w-full bg-[#090e17] border border-slate-700 rounded-lg '
                'px-3 py-2.5 text-sm text-white focus:border-cyan-400 focus:outline-none'
            )


class AbrirRNCForm(StyledModelForm):
    class Meta:
        model = NaoConformidade
        fields = ['titulo', 'descricao', 'prioridade']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4, 'maxlength': 3000}),
        }


class TratarRNCForm(StyledModelForm):
    comentario = forms.CharField(
        label='Comentário da atualização', required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'maxlength': 1000})
    )

    class Meta:
        model = NaoConformidade
        fields = ['situacao', 'acao_corretiva', 'responsavel', 'prazo']
        widgets = {
            'acao_corretiva': forms.Textarea(attrs={'rows': 4, 'maxlength': 3000}),
            'prazo': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].queryset = get_user_model().objects.filter(is_active=True)
        self.fields['responsavel'].empty_label = 'Não atribuído'
        self.fields['prazo'].input_formats = ['%Y-%m-%d']


class ItemFVSForm(StyledModelForm):
    class Meta:
        model = ItemFVS
        fields = ['descricao', 'resultado', 'observacao']
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2, 'maxlength': 1000}),
        }


class PlanejamentoMensalForm(StyledModelForm):
    class Meta:
        model = PlanejamentoMensal
        fields = ['torre', 'mes_referencia', 'percentual_planejado']
        widgets = {
            'mes_referencia': forms.TextInput(attrs={'type': 'month', 'placeholder': 'AAAA-MM'}),
            'percentual_planejado': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
        }

    def clean_mes_referencia(self):
        value = self.cleaned_data['mes_referencia']
        from .models import validar_mes_referencia
        validar_mes_referencia(value)
        return value
