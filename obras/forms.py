from django import forms
from django.contrib.auth import get_user_model

from .models import NaoConformidade, ItemFVS, PlanejamentoMensal, Torre, Apartamento, MedicaoMensal, ServicoObra, MarcoServico, validar_mes_referencia


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


class TorreForm(StyledModelForm):
    class Meta:
        model = Torre
        fields = ['nome', 'total_andares']
        widgets = {'total_andares': forms.NumberInput(attrs={'min': 1, 'max': 200})}


class ApartamentoForm(StyledModelForm):
    class Meta:
        model = Apartamento
        fields = ['torre', 'andar', 'numero']
        widgets = {'andar': forms.NumberInput(attrs={'min': 1, 'max': 200})}

    def clean(self):
        data = super().clean()
        torre, andar = data.get('torre'), data.get('andar')
        if torre and andar and andar > torre.total_andares:
            self.add_error('andar', 'O pavimento excede o total cadastrado nesta torre.')
        return data


class MedicaoMensalForm(StyledModelForm):
    class Meta:
        model = MedicaoMensal
        fields = ['apartamento', 'mes_referencia', 'etapa_atual', 'percentual_concluido']
        widgets = {
            'mes_referencia': forms.TextInput(attrs={'type': 'month', 'placeholder': 'AAAA-MM'}),
            'percentual_concluido': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
        }

    def clean_mes_referencia(self):
        value = self.cleaned_data['mes_referencia']
        validar_mes_referencia(value)
        return value



class ServicoObraForm(StyledModelForm):
    class Meta:
        model = ServicoObra
        fields = ['torre', 'codigo', 'descricao', 'peso_percentual']
        labels = {
            'torre': 'Torre', 'codigo': 'Código do serviço',
            'descricao': 'Descrição do serviço',
            'peso_percentual': 'Peso físico (%)',
        }
        widgets = {
            'peso_percentual': forms.NumberInput(attrs={'min': '0.01', 'max': '100', 'step': '0.01'}),
        }


class MarcoServicoForm(StyledModelForm):
    observacao = forms.CharField(
        label='Justificativa da alteração (opcional)',
        max_length=1000, required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'maxlength': 1000}),
    )

    class Meta:
        model = MarcoServico
        fields = ['servico', 'mes_referencia', 'previsto_acumulado', 'realizado_acumulado']
        labels = {
            'servico': 'Serviço',
            'mes_referencia': 'Mês de referência',
            'previsto_acumulado': 'Planejado acumulado do serviço (%)',
            'realizado_acumulado': 'Executado acumulado do serviço (%)',
        }
        widgets = {
            'mes_referencia': forms.TextInput(attrs={'type': 'month'}),
            'previsto_acumulado': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.01'}),
            'realizado_acumulado': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.01'}),
        }

    def __init__(self, *args, torre=None, **kwargs):
        super().__init__(*args, **kwargs)
        servicos = ServicoObra.objects.select_related('torre')
        if torre is not None:
            servicos = servicos.filter(torre=torre)
        self.fields['servico'].queryset = servicos.order_by('torre__nome', 'codigo')
        self.fields['previsto_acumulado'].help_text = (
            'Opcional se preencher Executado. Em branco preserva o valor anterior.'
        )
        self.fields['realizado_acumulado'].help_text = (
            'Opcional se preencher Planejado. Em branco preserva o valor anterior.'
        )

    def clean_mes_referencia(self):
        mes = self.cleaned_data['mes_referencia']
        validar_mes_referencia(mes)
        return mes



class EditarServicoObraForm(StyledModelForm):
    """Editar apenas dados que não identificam nem transferem o serviço entre torres."""
    class Meta:
        model = ServicoObra
        fields = ['descricao', 'peso_percentual']
        labels = {'descricao': 'Descrição do serviço', 'peso_percentual': 'Peso físico (%)'}
        widgets = {
            'peso_percentual': forms.NumberInput(attrs={'min': '0.01', 'max': '100', 'step': '0.01'}),
        }
