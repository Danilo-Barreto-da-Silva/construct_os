from django.contrib import admin
from django.urls import path
from django.conf import settings
from obras import views, operacoes, relatorios, planejamento_atividades, inteligencia_views, gemeo_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('inteligencia/', inteligencia_views.catalogo_inteligente, name='catalogo_inteligente'),
    path('inteligencia/tipologia/<int:tipologia_id>/etiquetas/', inteligencia_views.etiquetas_tipologia, name='etiquetas_tipologia'),
    path('inteligencia/tipologia/<int:tipologia_id>/comparar/', inteligencia_views.comparar_unidades_tipologia, name='comparar_unidades_tipologia'),
    path('inteligencia/projeto/item/<int:item_id>/conferir/', inteligencia_views.conferir_item_projeto, name='conferir_item_projeto'),
    path('inteligencia/projeto/documento/<int:documento_id>/arquivo/', inteligencia_views.documento_privado, name='documento_privado'),
    path('inteligencia/unidade/<int:apartamento_id>/', inteligencia_views.unidade_inteligente, name='unidade_inteligente'),
    path('inteligencia/unidade/<int:apartamento_id>/gemeo/', gemeo_views.gemeo_conceitual, name='gemeo_conceitual'),
    path('inteligencia/unidade/<int:apartamento_id>/peso/', inteligencia_views.salvar_peso_unidade, name='salvar_peso_unidade'),
    path('inteligencia/unidade/<int:apartamento_id>/validar/', inteligencia_views.validar_criterio_view, name='validar_criterio_view'),
    path('inteligencia/unidade/<int:apartamento_id>/enviar/', inteligencia_views.enviar_video_inteligente, name='enviar_video_inteligente'),
    path('inteligencia/unidade/<int:apartamento_id>/qr.svg', inteligencia_views.imagem_qr, name='imagem_qr'),
    path('inteligencia/qr/<uuid:token>/', inteligencia_views.vistoria_por_qr, name='vistoria_por_qr'),
    path('inteligencia/vistoria/<int:vistoria_id>/', inteligencia_views.detalhe_vistoria_inteligente, name='detalhe_vistoria_inteligente'),
    path('inteligencia/vistoria/<int:vistoria_id>/comparar/', inteligencia_views.comparar_vistoria_projeto, name='comparar_vistoria_projeto'),
    path('inteligencia/vistoria/<int:vistoria_id>/assistir/', inteligencia_views.video_reproducao, name='video_reproducao'),
    path('inteligencia/projeto/documento/<int:documento_id>/visualizar/', inteligencia_views.documento_visualizacao, name='documento_visualizacao'),
    path('inteligencia/vistoria/<int:vistoria_id>/video/', inteligencia_views.video_privado, name='video_privado'),
    path('inteligencia/vistoria/<int:vistoria_id>/reprocessar/', inteligencia_views.reprocessar_vistoria, name='reprocessar_vistoria'),
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
    path('planejamento/fisico/', planejamento_atividades.planejamento_fisico, name='planejamento_fisico'),
    path('cadastros/', operacoes.cadastros, name='cadastros'),
    path('relatorios/', relatorios.relatorios, name='relatorios'),
    path('relatorios/medicoes.csv', relatorios.exportar_medicoes_csv, name='exportar_medicoes_csv'),
    path('relatorios/rncs.csv', relatorios.exportar_rncs_csv, name='exportar_rncs_csv'),
    path('relatorios/servicos.csv', relatorios.exportar_servicos_csv, name='exportar_servicos_csv'),
    path('apartamento/<int:medicao_id>/avaliar/', views.avaliar_apartamento, name='avaliar_apartamento'),
    path('apartamento/<int:medicao_id>/historico/', views.historico_medicao, name='historico_medicao'),
]

# Arquivos técnicos e vídeos são privados. Nunca expor MEDIA_ROOT por rota estática.