"""Integração da vistoria paramétrica; todos os valores abaixo são FICTÍCIOS."""
import hashlib
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse, resolve, Resolver404

from .gemini_multimodal import (
    RelatoMultimodal, SugestaoEstruturada, processar_vistoria
)
from .models import (
    Torre, Apartamento, MedicaoMensal, TipologiaUnidade, AmbienteTipologia,
    ServicoTipologia, CriterioVistoria, UnidadeInteligente, PesoServicoUnidade,
    DocumentoProjeto, ItemEsperadoProjeto, VistoriaInteligente,
    SugestaoEtapaIA, MedicaoCriterio, EventoMedicaoCriterio,
)
from .parametros import progresso_unidade, validar_medicao


def video_teste(nome='teste.mp4'):
    return SimpleUploadedFile(
        nome, b'\x00\x00\x00\x18ftypisom' + b'\x00' * 100,
        content_type='video/mp4'
    )


def pdf_teste(nome='projeto.pdf'):
    return SimpleUploadedFile(
        nome, b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF',
        content_type='application/pdf'
    )


class InteligenciaTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        habilitar_media = override_settings(MEDIA_ROOT=self.tmp.name)
        habilitar_media.enable()
        self.addCleanup(habilitar_media.disable)
        User = get_user_model()
        self.gestor=User.objects.create_user('gestor-piloto',password='teste-1234',is_staff=True)
        self.operario=User.objects.create_user('operario-piloto',password='teste-1234')
        self.torre=Torre.objects.create(nome='Torre de Teste QR',total_andares=4)
        self.outra=Torre.objects.create(nome='Torre vizinha QR',total_andares=4)
        self.apto=Apartamento.objects.create(torre=self.torre,andar=1,numero='101')
        self.outro_apto=Apartamento.objects.create(torre=self.outra,andar=1,numero='101')
        self.tipo=TipologiaUnidade.objects.create(torre=self.torre,codigo='T1',nome='Tipologia teste')
        self.ambiente=AmbienteTipologia.objects.create(
            tipologia=self.tipo,codigo='SALA',nome='Sala de estar'
        )
        self.s1=ServicoTipologia.objects.create(
            tipologia=self.tipo,codigo='ALV',nome='Alvenaria',peso=Decimal('60')
        )
        self.s2=ServicoTipologia.objects.create(
            tipologia=self.tipo,codigo='ELE',nome='Elétrica',peso=Decimal('40')
        )
        self.c1=CriterioVistoria.objects.create(
            servico=self.s1,ambiente=self.ambiente,codigo='PAREDE',
            descricao='Paredes erguidas',peso=Decimal('100'),metodo='VISUAL'
        )
        self.c2=CriterioVistoria.objects.create(
            servico=self.s2,ambiente=self.ambiente,codigo='CAIXAS',
            descricao='Caixas de tomadas chumbadas',peso=Decimal('100'),metodo='VISUAL'
        )
        self.cfg=UnidadeInteligente.objects.create(
            apartamento=self.apto,tipologia=self.tipo
        )

    def test_pesos_e_medicoes_somam_ponderado_sem_ia(self):
        sem=progresso_unidade(self.cfg,'2026-11')
        self.assertIsNone(sem['percentual'])
        self.assertEqual(sem['n_validados'],0)
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=100,
        )
        faltante=progresso_unidade(self.cfg,'2026-11')
        self.assertIsNone(faltante['percentual'])
        self.assertEqual(faltante['n_validados'],1)
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c2,
            mes='2026-11',percentual=50,
        )
        resultado=progresso_unidade(self.cfg,'2026-11')
        self.assertEqual(resultado['percentual'],Decimal('80.00'))

    def test_pesos_personalizados_nao_misturam_com_herdados(self):
        PesoServicoUnidade.objects.create(unidade=self.cfg,servico=self.s1,peso=Decimal('40'))
        partial=progresso_unidade(self.cfg,'2026-11')
        self.assertFalse(partial['pesos_ok'])
        PesoServicoUnidade.objects.create(unidade=self.cfg,servico=self.s2,peso=Decimal('60'))
        validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-11',percentual=100)
        validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c2,mes='2026-11',percentual=50)
        self.assertEqual(progresso_unidade(self.cfg,'2026-11')['percentual'],Decimal('70.00'))

    def test_unidade_nao_aceita_tipologia_de_outra_torre(self):
        cfg=UnidadeInteligente(apartamento=self.outro_apto,tipologia=self.tipo)
        with self.assertRaises(ValidationError):
            cfg.full_clean()

    def test_servicos_e_criterios_nao_podem_ultrapassar_cem(self):
        s=ServicoTipologia(tipologia=self.tipo,codigo='OUT',nome='Outro',peso=Decimal('1'))
        with self.assertRaises(ValidationError):
            s.full_clean()
        c=CriterioVistoria(servico=self.s1,codigo='OUT',descricao='Extra',peso=Decimal('1'))
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_mensuracao_exige_staff_e_audita_alteracoes(self):
        with self.assertRaises(PermissionDenied):
            validar_medicao(
                autor=self.operario,unidade=self.cfg,criterio=self.c1,
                mes='2026-11',percentual=10
            )
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=40,observacao='Teste inicial'
        )
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=50,observacao='Correção de vistoria'
        )
        self.assertEqual(MedicaoCriterio.objects.count(),1)
        self.assertEqual(EventoMedicaoCriterio.objects.count(),2)
        self.assertEqual(
            list(EventoMedicaoCriterio.objects.order_by('pk').values_list('novo',flat=True)),
            [Decimal('40'),Decimal('50')]
        )

    def test_mensuracao_de_mes_posterior_nao_retrocede(self):
        validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-10',percentual=70)
        with self.assertRaises(ValidationError):
            validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-11',percentual=50)
        self.assertEqual(MedicaoCriterio.objects.count(),1)

    def test_mensuracao_mensal_herda_ultimo_valor_confirmado(self):
        validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-10',percentual=20)
        validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c2,mes='2026-10',percentual=0)
        self.assertEqual(progresso_unidade(self.cfg,'2026-11')['percentual'],Decimal('12.00'))
        self.assertIsNone(progresso_unidade(self.cfg,'2026-09')['percentual'])

    def test_mes_invalido_ou_fora_de_faixa_rejeitado(self):
        with self.assertRaises(ValidationError):
            validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-13',percentual=20)
        with self.assertRaises(ValidationError):
            validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-11',percentual=101)

    def test_peso_unidade_nao_pode_mudar_apos_medicao(self):
        item=PesoServicoUnidade.objects.create(unidade=self.cfg,servico=self.s1,peso=Decimal('40'))
        PesoServicoUnidade.objects.create(unidade=self.cfg,servico=self.s2,peso=Decimal('60'))
        validar_medicao(autor=self.gestor,unidade=self.cfg,criterio=self.c1,mes='2026-11',percentual=20)
        item.peso=Decimal('45')
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_qr_requer_login_e_nao_autoriza_sem_sessao(self):
        link=reverse('vistoria_por_qr',kwargs={'token':self.cfg.token_qr})
        resp=self.client.get(link)
        self.assertEqual(resp.status_code,302)
        self.assertIn('/login/',resp.url)
        self.client.force_login(self.operario)
        resp=self.client.get(link)
        self.assertRedirects(resp,reverse('unidade_inteligente',args=[self.apto.pk]))
        svg=self.client.get(reverse('imagem_qr',args=[self.apto.pk]))
        self.assertEqual(svg.status_code,200)
        self.assertEqual(svg['Content-Type'],'image/svg+xml')
        self.assertIn(b'<svg',svg.content)
        self.assertIn('no-store',svg['Cache-Control'])

    def test_paginas_catalogo_e_unidade_abrem(self):
        self.client.force_login(self.operario)
        self.assertContains(self.client.get(reverse('catalogo_inteligente')),'Projetos, tipologias')
        self.assertContains(self.client.get(reverse('unidade_inteligente',args=[self.apto.pk])),'Gravar vistoria')
        resp=self.client.post(reverse('catalogo_inteligente'),{
            'acao':'tipologia','torre':self.torre.pk,'codigo':'T2','nome':'Outra'
        })
        self.assertEqual(resp.status_code,403)

    def test_video_invalido_rejeitado(self):
        self.client.force_login(self.operario)
        resp=self.client.post(reverse('enviar_video_inteligente',args=[self.apto.pk]),{
            'arquivo':SimpleUploadedFile('malicioso.mp4',b'not really a video'),
            'observacao':'Teste'
        })
        self.assertEqual(resp.status_code,302)
        self.assertFalse(VistoriaInteligente.objects.exists())

    def test_video_guardado_privado_sem_alterar_fvs(self):
        med=MedicaoMensal.objects.create(
            apartamento=self.apto,mes_referencia='2026-11',
            status_iso='PENDENTE',percentual_concluido=0,
        )
        self.client.force_login(self.operario)
        resp=self.client.post(reverse('enviar_video_inteligente',args=[self.apto.pk]),{
            'arquivo':video_teste(),'observacao':'Caixas na sala, somente teste.'
        })
        self.assertEqual(resp.status_code,302)
        obj=VistoriaInteligente.objects.get()
        self.assertEqual(obj.estado,'PENDENTE')
        self.assertIn('privado_vistorias/',obj.arquivo.name)
        med.refresh_from_db()
        self.assertEqual(med.status_iso,'PENDENTE')
        self.assertEqual(med.percentual_concluido,0)
        self.assertFalse(MedicaoCriterio.objects.exists())
        self.assertRaises(Resolver404,resolve,'/media/'+obj.arquivo.name)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('video_privado',args=[obj.pk])).status_code,302)
        self.client.force_login(self.operario)
        resp=self.client.get(reverse('video_privado',args=[obj.pk]))
        self.assertEqual(resp.status_code,200)
        self.assertIn('no-store',resp['Cache-Control'])

    def test_pdf_invalido_e_pdf_valido_protegido(self):
        self.client.force_login(self.gestor)
        url=reverse('catalogo_inteligente')+f'?tipo={self.tipo.pk}'
        invalido=self.client.post(url,{
            'acao':'documento','tipologia':self.tipo.pk,'disciplina':'ARQ',
            'nome':'Planta fictícia','revisao':'R00',
            'arquivo':SimpleUploadedFile('bad.pdf',b'hello'),
        })
        self.assertEqual(invalido.status_code,200)
        self.assertFalse(DocumentoProjeto.objects.exists())
        valido=self.client.post(url,{
            'acao':'documento','tipologia':self.tipo.pk,'disciplina':'ARQ',
            'nome':'Planta fictícia','revisao':'R00','arquivo':pdf_teste(),
        })
        self.assertEqual(valido.status_code,302)
        doc=DocumentoProjeto.objects.get()
        self.assertEqual(doc.sha256,hashlib.sha256(pdf_teste().read()).hexdigest())
        self.client.logout()
        self.assertEqual(self.client.get(reverse('documento_privado',args=[doc.pk])).status_code,302)
        self.client.force_login(self.gestor)
        dl=self.client.get(reverse('documento_privado',args=[doc.pk]))
        self.assertEqual(dl.status_code,200)
        self.assertIn('attachment',dl['Content-Disposition'])

    def test_ia_nao_cria_medicao_sem_acao_do_profissional(self):
        visto=VistoriaInteligente.objects.create(
            apartamento=self.apto,enviado_por=self.gestor,
            arquivo=video_teste(),observacao='Há caixas elétricas.',
        )
        resultado=RelatoMultimodal(
            resumo='Paredes e caixas parcialmente aparentes nas imagens do teste.',
            transcricao_narrada='Caixas elétricas na sala.',
            sugestoes=[
                SugestaoEstruturada(
                    chave='ELE/CAIXAS',fonte='AUDIO',percentual_sugerido=90,
                    instante_segundos=5,justificativa='Declarado no áudio sem imagem suficiente.'
                ),
                SugestaoEstruturada(
                    chave='ALV/PAREDE',fonte='VISUAL',percentual_sugerido=40,
                    instante_segundos=10,justificativa='Parte da alvenaria visível.'
                ),
            ]
        )
        with patch('obras.gemini_multimodal._consultar_gemini',return_value=resultado):
            self.assertTrue(processar_vistoria(visto.pk))
        visto.refresh_from_db()
        self.assertEqual(visto.estado,'ANALISADA')
        self.assertEqual(SugestaoEtapaIA.objects.count(),2)
        audio=SugestaoEtapaIA.objects.get(criterio=self.c2)
        self.assertIsNone(audio.percentual_sugerido)
        self.assertFalse(MedicaoCriterio.objects.exists())
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(reverse('detalhe_vistoria_inteligente',args=[visto.pk])),'Sugestões por critério')

    def test_item_de_projeto_apenas_conferido_entra_no_prompt(self):
        doc=DocumentoProjeto.objects.create(
            tipologia=self.tipo,nome='Planta fictícia',disciplina='ELE',
            arquivo=pdf_teste(),enviado_por=self.gestor
        )
        item=ItemEsperadoProjeto.objects.create(
            documento=doc,criterio=self.c2,pagina=1,
            referencia='PONTO-TESTE',descricao='Ponto de teste fictício',
        )
        from .gemini_multimodal import preparar_contexto
        visto=VistoriaInteligente.objects.create(
            apartamento=self.apto,arquivo=video_teste(),enviado_por=self.gestor
        )
        _,_,refs=preparar_contexto(visto)
        self.assertFalse(refs)
        item.conferido=True
        item.conferido_por=self.gestor
        item.save()
        _,_,refs=preparar_contexto(visto)
        self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]['folha'],1)

    def test_reprocessar_exige_staff_e_falha_existente(self):
        visto=VistoriaInteligente.objects.create(
            apartamento=self.apto,arquivo=video_teste(),estado='ERRO'
        )
        url=reverse('reprocessar_vistoria',args=[visto.pk])
        self.client.force_login(self.operario)
        self.assertEqual(self.client.post(url).status_code,403)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.post(url).status_code,302)
        visto.refresh_from_db()
        self.assertEqual(visto.estado,'PENDENTE')

    def test_servico_e_criterio_nao_mudam_depois_de_uso(self):
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=10
        )
        extra=ServicoTipologia(
            tipologia=self.tipo,codigo='PINT',nome='Pintura',peso=Decimal('1')
        )
        with self.assertRaises(ValidationError):
            extra.full_clean()
        self.s1.peso=Decimal('59')
        with self.assertRaises(ValidationError):
            self.s1.full_clean()
        self.s1.refresh_from_db()
        criterio_novo=CriterioVistoria(
            servico=self.s1,codigo='PRUMO',descricao='Prumo',peso=Decimal('1')
        )
        with self.assertRaises(ValidationError):
            criterio_novo.full_clean()
        self.c1.peso=Decimal('99')
        with self.assertRaises(ValidationError):
            self.c1.full_clean()

    def test_novo_override_depois_de_medir_e_bloqueado(self):
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=25
        )
        novo=PesoServicoUnidade(
            unidade=self.cfg,servico=self.s1,peso=Decimal('60')
        )
        with self.assertRaises(ValidationError):
            novo.full_clean()

    def test_comando_tipologia_piloto_gera_somente_dados_ficticios(self):
        nova_torre=Torre.objects.create(nome='Nova torre piloto IA',total_andares=2)
        novo_apto=Apartamento.objects.create(torre=nova_torre,andar=1,numero='201')
        legado=MedicaoMensal.objects.create(
            apartamento=novo_apto,mes_referencia='2026-11',
            percentual_concluido=33,status_iso='PENDENTE'
        )
        call_command(
            'criar_tipologia_piloto',torre_id=nova_torre.pk,apto_id=novo_apto.pk,
            confirmar_demo=True,verbosity=0
        )
        criado=UnidadeInteligente.objects.get(apartamento=novo_apto)
        self.assertEqual(criado.tipologia.codigo,'PILOTO-IA')
        self.assertEqual(
            sum(ServicoTipologia.objects.filter(tipologia=criado.tipologia)
                .values_list('peso',flat=True)),Decimal('100')
        )
        self.assertEqual(
            CriterioVistoria.objects.filter(servico__tipologia=criado.tipologia).count(),
            17
        )
        self.assertIsNone(progresso_unidade(criado,'2026-11')['percentual'])
        legado.refresh_from_db()
        self.assertEqual(legado.percentual_concluido,33)
        self.assertEqual(legado.status_iso,'PENDENTE')
        with self.assertRaises(CommandError):
            call_command(
                'criar_tipologia_piloto',torre_id=nova_torre.pk,apto_id=novo_apto.pk,
                confirmar_demo=True,verbosity=0
            )

    def test_etiquetas_qr_imprimiveis_restritas_a_gestor(self):
        url=reverse('etiquetas_tipologia',args=[self.tipo.pk])
        self.assertEqual(self.client.get(url).status_code,302)
        self.client.force_login(self.operario)
        self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.gestor)
        resp=self.client.get(url)
        self.assertEqual(resp.status_code,200)
        self.assertContains(resp,'Apartamento 101')
        self.assertContains(resp,'window.print()')
        self.assertContains(resp,'/qr.svg')

    def test_comparacao_lado_a_lado_so_de_documentos_da_tipologia(self):
        doc=DocumentoProjeto.objects.create(
            tipologia=self.tipo,disciplina='ARQ',nome='Desenho teste',
            arquivo=pdf_teste(),enviado_por=self.gestor
        )
        visto=VistoriaInteligente.objects.create(
            apartamento=self.apto,arquivo=video_teste(),enviado_por=self.gestor
        )
        self.client.force_login(self.gestor)
        pagina=self.client.get(reverse('comparar_vistoria_projeto',args=[visto.pk]))
        self.assertEqual(pagina.status_code,200)
        self.assertContains(pagina,'Comparação visual assistida')
        self.assertContains(pagina,'Desenho teste')
        self.assertContains(pagina,'/assistir/')
        self.assertContains(pagina,'/visualizar/')
        pdf=self.client.get(reverse('documento_visualizacao',args=[doc.pk]))
        self.assertEqual(pdf.status_code,200)
        self.assertEqual(pdf['Content-Type'],'application/pdf')
        self.assertEqual(pdf['X-Frame-Options'],'SAMEORIGIN')
        video=self.client.get(reverse('video_reproducao',args=[visto.pk]))
        self.assertEqual(video.status_code,200)
        self.assertEqual(video['Content-Type'],'video/mp4')
        self.client.logout()
        self.assertEqual(self.client.get(reverse('documento_visualizacao',args=[doc.pk])).status_code,302)
        self.assertEqual(self.client.get(reverse('video_reproducao',args=[visto.pk])).status_code,302)

    def test_historico_de_medicao_por_criterio_aparece_na_ficha(self):
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=40,observacao='Primeira medição fictícia'
        )
        validar_medicao(
            autor=self.gestor,unidade=self.cfg,criterio=self.c1,
            mes='2026-11',percentual=50,observacao='Segunda medição fictícia'
        )
        self.client.force_login(self.gestor)
        resp=self.client.get(reverse('unidade_inteligente',args=[self.apto.pk]),{'mes':'2026-11'})
        self.assertContains(resp,'Histórico de medições verificadas')
        self.assertContains(resp,'Primeira medição fictícia')
        self.assertContains(resp,'Segunda medição fictícia')
        self.assertEqual(len(resp.context['historico_medicoes']),2)
