from django.contrib import admin
from .models import HistoricoMedicao


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
