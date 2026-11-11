from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import obras.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('obras', '0006_auditar_metas'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServicoObra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=20)),
                ('descricao', models.CharField(max_length=160)),
                ('peso_percentual', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal('0.01')), django.core.validators.MaxValueValidator(100)])),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('torre', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='servicos_fisicos', to='obras.torre')),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['torre_id', 'codigo'],
                'constraints': [models.UniqueConstraint(fields=('torre', 'codigo'), name='servico_codigo_unico_torre')],
            },
        ),
        migrations.CreateModel(
            name='MarcoServico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes_referencia', models.CharField(max_length=7, validators=[obras.models.validar_mes_referencia])),
                ('previsto_acumulado', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('realizado_acumulado', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='marcos', to='obras.servicoobra')),
                ('atualizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['mes_referencia', 'servico__codigo'],
                'constraints': [models.UniqueConstraint(fields=('servico', 'mes_referencia'), name='marco_servico_mes_unico')],
            },
        ),
        migrations.CreateModel(
            name='EventoMarcoServico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('previsto_anterior', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('previsto_novo', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('realizado_anterior', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('realizado_novo', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('observacao', models.TextField(blank=True, default='', max_length=1000)),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('marco', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='eventos', to='obras.marcoservico')),
            ],
            options={'ordering': ['-criado_em', '-id']},
        ),
    ]
