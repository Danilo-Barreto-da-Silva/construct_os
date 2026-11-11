from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('obras', '0007_servicos_curva_s'),
    ]
    operations = [
        migrations.CreateModel(
            name='EventoServicoObra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('descricao_anterior', models.CharField(max_length=160)),
                ('descricao_nova', models.CharField(max_length=160)),
                ('peso_anterior', models.DecimalField(decimal_places=2, max_digits=5)),
                ('peso_novo', models.DecimalField(decimal_places=2, max_digits=5)),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisoes', to='obras.servicoobra')),
            ],
            options={'ordering': ['-criado_em', '-id']},
        ),
    ]
