import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
from django.core.validators import MinValueValidator, MaxValueValidator
import django.db.models.deletion
import obras.modelos_inteligentes
import obras.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('obras', '0008_revisoes_servicos'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipologiaUnidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=30)),
                ('nome', models.CharField(max_length=120)),
                ('descricao', models.TextField(blank=True, default='')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('torre', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tipologias', to='obras.torre')),
            ],
            options={'ordering': ['torre__nome', 'codigo'],
                'constraints': [models.UniqueConstraint(fields=('torre','codigo'), name='tipologia_unica_torre')]},
        ),
        migrations.CreateModel(
            name='AmbienteTipologia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=30)),
                ('nome', models.CharField(max_length=100)),
                ('area_m2', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True,
                                                validators=[MinValueValidator(Decimal('0.01'))])),
                ('tipologia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ambientes', to='obras.tipologiaunidade')),
            ],
            options={'ordering': ['tipologia_id', 'codigo'],
                'constraints': [models.UniqueConstraint(fields=('tipologia','codigo'), name='ambiente_unico_tipologia')]},
        ),
        migrations.CreateModel(
            name='ServicoTipologia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=30)),
                ('nome', models.CharField(max_length=120)),
                ('peso', models.DecimalField(decimal_places=2, max_digits=5,
                                            validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])),
                ('tipologia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='servicos', to='obras.tipologiaunidade')),
            ],
            options={'ordering': ['tipologia_id', 'codigo'],
                'constraints': [models.UniqueConstraint(fields=('tipologia','codigo'), name='servico_unico_tipologia')]},
        ),
        migrations.CreateModel(
            name='CriterioVistoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=40)),
                ('descricao', models.CharField(max_length=220)),
                ('peso', models.DecimalField(decimal_places=2, max_digits=5,
                                             validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])),
                ('metodo', models.CharField(choices=[('VISUAL','Inspeção visual'),('TESTE','Ensaio ou teste técnico'),('MEDICAO','Medição instrumental'),('DOCUMENTAL','Comprovação documental')], default='VISUAL', max_length=12)),
                ('orientacao', models.TextField(blank=True, default='')),
                ('ambiente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='criterios', to='obras.ambientetipologia')),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='criterios', to='obras.servicotipologia')),
            ],
            options={'ordering': ['servico_id', 'codigo'],
                'constraints': [models.UniqueConstraint(fields=('servico','codigo'), name='criterio_unico_servico')]},
        ),
        migrations.CreateModel(
            name='UnidadeInteligente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_qr', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('apartamento', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='config_inteligente', to='obras.apartamento')),
                ('tipologia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='unidades', to='obras.tipologiaunidade')),
            ],
        ),
        migrations.CreateModel(
            name='PesoServicoUnidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('peso', models.DecimalField(decimal_places=2, max_digits=5, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(100)])),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pesos_unidades', to='obras.servicotipologia')),
                ('unidade', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pesos_proprios', to='obras.unidadeinteligente')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('unidade','servico'), name='peso_unico_unidade_servico')]},
        ),
        migrations.CreateModel(
            name='DocumentoProjeto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('disciplina', models.CharField(choices=[('ARQ','Arquitetônico'),('ELE','Elétrico'),('AGUA','Água'),('ESG','Esgoto'),('EST','Estrutural'),('OUT','Outros')], max_length=5)),
                ('nome', models.CharField(max_length=150)),
                ('revisao', models.CharField(blank=True, default='', max_length=40)),
                ('arquivo', models.FileField(upload_to=obras.modelos_inteligentes.arquivo_privado)),
                ('sha256', models.CharField(blank=True, default='', max_length=64)),
                ('enviado_em', models.DateTimeField(auto_now_add=True)),
                ('enviado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('tipologia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documentos', to='obras.tipologiaunidade')),
            ],
            options={'ordering': ['-enviado_em', '-id']},
        ),
        migrations.CreateModel(
            name='ItemEsperadoProjeto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pagina', models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])),
                ('referencia', models.CharField(max_length=120)),
                ('descricao', models.TextField(max_length=1000)),
                ('quantidade', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[MinValueValidator(0)])),
                ('unidade_medida', models.CharField(blank=True, default='', max_length=20)),
                ('conferido', models.BooleanField(default=False)),
                ('conferido_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_projeto_conferidos', to=settings.AUTH_USER_MODEL)),
                ('criterio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='itens_projeto', to='obras.criteriovistoria')),
                ('documento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='itens_esperados', to='obras.documentoprojeto')),
            ],
        ),
        migrations.CreateModel(
            name='VistoriaInteligente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(upload_to=obras.modelos_inteligentes.arquivo_privado)),
                ('observacao', models.TextField(blank=True, default='', max_length=2000)),
                ('estado', models.CharField(choices=[('PENDENTE','Aguardando análise'),('PROCESSANDO','Processando'),('ANALISADA','Sugestões disponíveis'),('ERRO','Erro de processamento')], default='PENDENTE', max_length=12)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('processado_em', models.DateTimeField(blank=True, null=True)),
                ('modelo', models.CharField(blank=True, default='', max_length=80)),
                ('transcricao_ia', models.TextField(blank=True, default='')),
                ('resumo_ia', models.TextField(blank=True, default='')),
                ('erro_publico', models.CharField(blank=True, default='', max_length=300)),
                ('apartamento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vistorias_inteligentes', to='obras.apartamento')),
                ('enviado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-criado_em', '-id']},
        ),
        migrations.CreateModel(
            name='SugestaoEtapaIA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fonte', models.CharField(choices=[('VISUAL','Evidência visual'),('AUDIO','Declaração do áudio'),('AMBAS','Áudio e vídeo'),('INCERTO','Não verificável')], default='INCERTO', max_length=8)),
                ('percentual_sugerido', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ('instante_segundos', models.PositiveIntegerField(blank=True, null=True)),
                ('justificativa', models.TextField(max_length=1500)),
                ('revisado_em', models.DateTimeField(blank=True, null=True)),
                ('criterio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sugestoes', to='obras.criteriovistoria')),
                ('revisado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('vistoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sugestoes', to='obras.vistoriainteligente')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('vistoria','criterio'), name='sugestao_unica_criterio_video')]},
        ),
        migrations.CreateModel(
            name='MedicaoCriterio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes_referencia', models.CharField(max_length=7, validators=[obras.models.validar_mes_referencia])),
                ('percentual_validado', models.DecimalField(decimal_places=2, max_digits=5, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('apartamento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='medicoes_criterios', to='obras.apartamento')),
                ('criterio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='medicoes', to='obras.criteriovistoria')),
                ('validado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('vistoria_origem', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='obras.vistoriainteligente')),
            ],
            options={'constraints':[models.UniqueConstraint(fields=('apartamento','criterio','mes_referencia'), name='criterio_apto_mes_unico')]},
        ),
        migrations.CreateModel(
            name='EventoMedicaoCriterio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registrado_em', models.DateTimeField(auto_now_add=True)),
                ('anterior', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('novo', models.DecimalField(decimal_places=2, max_digits=5)),
                ('observacao', models.CharField(blank=True, default='', max_length=500)),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('medicao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='eventos', to='obras.medicaocriterio')),
            ],
            options={'ordering': ['-registrado_em','-id']},
        ),
    ]
