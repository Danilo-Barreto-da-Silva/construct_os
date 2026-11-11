from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import obras.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('obras', '0003_historico_fvs'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanejamentoMensal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes_referencia', models.CharField(max_length=7, validators=[obras.models.validar_mes_referencia])),
                ('percentual_planejado', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('registrado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('torre', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='planejamentos', to='obras.torre')),
            ],
            options={
                'ordering': ['mes_referencia', 'torre__nome'],
                'constraints': [models.UniqueConstraint(fields=('torre', 'mes_referencia'), name='planejamento_mes_torre_unico')],
            },
        ),
        migrations.CreateModel(
            name='NaoConformidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=140)),
                ('descricao', models.TextField(max_length=3000)),
                ('prioridade', models.CharField(choices=[('BAIXA', 'Baixa'), ('MEDIA', 'Média'), ('ALTA', 'Alta'), ('CRITICA', 'Crítica')], default='MEDIA', max_length=10)),
                ('situacao', models.CharField(choices=[('ABERTA', 'Aberta'), ('TRATAMENTO', 'Em tratamento'), ('RESOLVIDA', 'Resolvida')], default='ABERTA', max_length=12)),
                ('acao_corretiva', models.TextField(blank=True, max_length=3000)),
                ('prazo', models.DateField(blank=True, null=True)),
                ('aberta_em', models.DateTimeField(auto_now_add=True)),
                ('atualizada_em', models.DateTimeField(auto_now=True)),
                ('encerrada_em', models.DateTimeField(blank=True, null=True)),
                ('aberta_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rncs_abertas', to=settings.AUTH_USER_MODEL)),
                ('encerrada_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rncs_encerradas', to=settings.AUTH_USER_MODEL)),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rncs_atribuidas', to=settings.AUTH_USER_MODEL)),
                ('medicao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rncs', to='obras.medicaomensal')),
            ],
            options={'ordering': ['-aberta_em', '-id']},
        ),
        migrations.CreateModel(
            name='ItemFVS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=180)),
                ('resultado', models.CharField(choices=[('PENDENTE', 'Não verificado'), ('CONFORME', 'Conforme'), ('NAO_CONFORME', 'Não conforme'), ('NA', 'Não se aplica')], default='PENDENTE', max_length=15)),
                ('observacao', models.TextField(blank=True, max_length=1000)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('medicao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='itens_fvs', to='obras.medicaomensal')),
                ('verificado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['id']},
        ),
        migrations.CreateModel(
            name='EventoRNC',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('situacao_anterior', models.CharField(blank=True, max_length=12)),
                ('situacao_nova', models.CharField(max_length=12)),
                ('descricao', models.TextField()),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('rnc', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='eventos', to='obras.naoconformidade')),
            ],
            options={'ordering': ['-criado_em', '-id']},
        ),
        migrations.CreateModel(
            name='EventoFVS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('resultado_anterior', models.CharField(blank=True, max_length=15)),
                ('resultado_novo', models.CharField(max_length=15)),
                ('observacao', models.TextField(blank=True)),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='eventos', to='obras.itemfvs')),
            ],
            options={'ordering': ['-criado_em', '-id']},
        ),
    ]
