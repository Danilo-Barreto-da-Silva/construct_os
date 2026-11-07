from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from obras import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_sistema, name='login_sistema'),
    path('sair/', views.logout_sistema, name='logout_sistema'),
    path('', views.painel_principal, name='painel_principal'),
    path('popular-demo/', views.popular_dados_demo, name='popular_dados_demo'),
    path('apartamento/<int:medicao_id>/avaliar/', views.avaliar_apartamento, name='avaliar_apartamento'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)