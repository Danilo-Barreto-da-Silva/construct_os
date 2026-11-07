from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('obras', '0005_validar_cadastros'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoPlanejamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registrado_em', models.DateTimeField(auto_now_add=True)),
                ('percentual_anterior', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('percentual_novo', models.DecimalField(decimal_places=2, max_digits=5)),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('planejamento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='eventos', to='obras.planejamentomensal')),
            ],
            options={'ordering': ['-registrado_em', '-id']},
        ),
    ]
