from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [('obras', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='medicaomensal',
            name='sugestao_ia',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='medicaomensal',
            name='percentual_concluido',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
        migrations.AlterField(
            model_name='medicaomensal',
            name='status_iso',
            field=models.CharField(choices=[('CONFORME', 'Conforme (ISO 9001 OK)'), ('PENDENTE', 'Pendente de FVS'), ('NAO_CONFORME', 'Não Conforme (RNC Aberta)')], default='PENDENTE', max_length=20),
        ),
    ]
