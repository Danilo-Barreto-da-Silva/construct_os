from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('obras', '0002_separar_fvs_e_sugestao_ia'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicaomensal',
            name='fvs_aprovada_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='medicaomensal',
            name='fvs_aprovada_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fvs_aprovadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='HistoricoMedicao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registrado_em', models.DateTimeField(auto_now_add=True)),
                ('origem', models.CharField(choices=[('MANUAL', 'Atualização manual'), ('SUGESTAO_IA', 'Sugestão de IA')], default='MANUAL', max_length=20)),
                ('percentual_anterior', models.IntegerField(default=0)),
                ('percentual_novo', models.IntegerField(default=0)),
                ('status_anterior', models.CharField(default='PENDENTE', max_length=20)),
                ('status_novo', models.CharField(default='PENDENTE', max_length=20)),
                ('etapa_anterior', models.CharField(blank=True, default='', max_length=100)),
                ('etapa_nova', models.CharField(blank=True, default='', max_length=100)),
                ('observacao', models.TextField(blank=True, default='')),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('medicao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='historico', to='obras.medicaomensal')),
            ],
            options={'ordering': ['-registrado_em', '-id']},
        ),
    ]
