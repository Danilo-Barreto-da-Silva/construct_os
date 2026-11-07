from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from obras import views, operacoes, relatorios

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_sistema, name='login_sistema'),
    path('sair/', views.logout_sistema, name='logout_sistema'),
    path('', views.painel_principal, name='painel_principal'),
    path('popular-demo/', views.popular_dados_demo, name='popular_dados_demo'),
    path('qualidade/rncs/', operacoes.lista_rncs, name='lista_rncs'),
    path('qualidade/rnc/abrir/<int:medicao_id>/', operacoes.abrir_rnc_pagina, name='abrir_rnc_pagina'),
    path('qualidade/rnc/<int:rnc_id>/', operacoes.detalhe_rnc, name='detalhe_rnc'),
    path('qualidade/rnc/<int:rnc_id>/tratar/', operacoes.tratar_rnc, name='tratar_rnc'),
    path('qualidade/fvs/<int:medicao_id>/', operacoes.checklist_fvs, name='checklist_fvs'),
    path('qualidade/fvs/<int:medicao_id>/item/novo/', operacoes.salvar_item_fvs_view, name='criar_item_fvs'),
    path('qualidade/fvs/<int:medicao_id>/item/<int:item_id>/', operacoes.salvar_item_fvs_view, name='editar_item_fvs'),
    path('planejamento/', operacoes.planejamento, name='planejamento'),
    path('cadastros/', operacoes.cadastros, name='cadastros'),
    path('relatorios/', relatorios.relatorios, name='relatorios'),
    path('relatorios/medicoes.csv', relatorios.exportar_medicoes_csv, name='exportar_medicoes_csv'),
    path('relatorios/rncs.csv', relatorios.exportar_rncs_csv, name='exportar_rncs_csv'),
    path('apartamento/<int:medicao_id>/avaliar/', views.avaliar_apartamento, name='avaliar_apartamento'),
    path('apartamento/<int:medicao_id>/historico/', views.historico_medicao, name='historico_medicao'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)