from django.db import migrations, models
import django.core.validators
import obras.models


class Migration(migrations.Migration):
    dependencies = [('obras', '0004_qualidade_planejamento')]

    operations = [
        migrations.AlterField(
            model_name='torre',
            name='total_andares',
            field=models.IntegerField(default=6, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(200)]),
        ),
        migrations.AlterField(
            model_name='apartamento',
            name='andar',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(200)]),
        ),
        migrations.AlterField(
            model_name='medicaomensal',
            name='mes_referencia',
            field=models.CharField(default='2026-11', max_length=7, validators=[obras.models.validar_mes_referencia]),
        ),
        migrations.AddConstraint(
            model_name='apartamento',
            constraint=models.UniqueConstraint(fields=('torre', 'numero'), name='apartamento_numero_unico_por_torre'),
        ),
        migrations.AddConstraint(
            model_name='medicaomensal',
            constraint=models.UniqueConstraint(fields=('apartamento', 'mes_referencia'), name='medicao_por_apto_mes_unica'),
        ),
    ]
