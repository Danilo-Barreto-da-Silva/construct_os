from django.contrib import admin
from .models import (
    HistoricoMedicao, Torre, Apartamento, MedicaoMensal,
    PlanejamentoMensal, EventoPlanejamento, NaoConformidade, EventoRNC, ItemFVS, EventoFVS,
)


@admin.register(HistoricoMedicao)
class HistoricoMedicaoAdmin(admin.ModelAdmin):
    list_display = (
        'registrado_em', 'medicao', 'origem', 'autor',
        'percentual_anterior', 'percentual_novo',
        'status_anterior', 'status_novo',
    )
    list_filter = ('origem', 'status_novo', 'registrado_em')
    search_fields = ('medicao__apartamento__numero', 'medicao__apartamento__torre__nome', 'autor__username')
    readonly_fields = (
        'medicao', 'autor', 'registrado_em', 'origem',
        'percentual_anterior', 'percentual_novo',
        'status_anterior', 'status_novo',
        'etapa_anterior', 'etapa_nova', 'observacao',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(
    Torre, Apartamento, MedicaoMensal, PlanejamentoMensal,
    NaoConformidade, EventoRNC, ItemFVS, EventoFVS, EventoPlanejamento,
)
class CadastroSomenteConsultaAdmin(admin.ModelAdmin):
    """Inspeção pelo admin sem operações que ignorariam o histórico operacional."""
    list_display = ('__str__',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
