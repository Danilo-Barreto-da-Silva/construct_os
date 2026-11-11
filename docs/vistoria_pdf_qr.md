# SGO.IA — projetos, tipologias, QR Code e vistoria por vídeo + áudio

> **Protótipo acadêmico.** Este módulo auxilia a análise de evidências; NÃO faz inspeção normativa, medição contratual, aprovação de FVS, aceitação técnica ou cálculo financeiro automaticamente.

## O fluxo

1. Gestor cria uma **tipologia** dentro de uma **torre**.
2. Cadastros definem **ambientes**, **serviços com pesos** (total = 100%) e **critérios por serviço** (total interno = 100% por serviço).
3. Cada apartamento é vinculado a uma tipologia. Opcionalmente recebe um conjunto COMPLETO de pesos próprios (soma = 100%).
4. Documentos arquitetônicos/elétricos/hidrossanitários/estruturais são enviados como **PDF privado** e identificados pela **revisão**.
5. Cada **item esperado** é vinculado ao documento, à folha e ao critério. Um profissional precisa **conferir** sua interpretação antes que o item seja utilizado pelo prompt da IA.
6. O gestor pode **imprimir uma folha de QR Codes** de todas as unidades vinculadas. O engenheiro ou encarregado autenticado lê o QR Code exclusivo do apartamento, abre a ficha no celular e grava vídeo com narração (ou envia um arquivo).
7. O sistema oferece uma vista **vídeo × projeto PDF lado a lado** para conferência humana. Não é sobreposição automática BIM nem validação espacial. O comando separado `processar_vistorias` envia apenas o vídeo selecionado e os critérios/requisitos conferidos ao Gemini. A IA separa evidência **visual**, **áudio declarado**, **ambas** ou **incerto**.
8. Uma pessoa autorizada insere a porcentagem **verificada** de cada critério, com data, autor e origem. A IA não grava esses números.
9. O percentual de serviço = Σ(peso interno × percentual confirmado / 100). O apartamento = Σ(peso do serviço × percentual do serviço / 100).

**Não há soma dupla**: um critério é ponderado primeiro dentro do serviço e depois dentro do apartamento. Não use o mesmo peso de estrutura compartilhada em múltiplos apartamentos sem uma metodologia explícita aprovada.

## Ausências e versionamento

- Ausência de medição é **desconhecido**, não 0. Para algo não iniciado, o técnico registra **0%** explicitamente.
- O progresso de um critério validado continua válido nos meses seguintes até ser substituído por nova verificação. A ficha mostra o **histórico de medições verificadas**, com autor e valores antigos/novos.
- A soma de pesos da tipologia, dos critérios de cada serviço e (quando utilizados) dos pesos próprios da unidade precisa dar 100%.
- Após a primeira medição validada da tipologia, o conjunto de serviços, critérios e pesos fica congelado. Não recalibrar retroativamente históricos: use outra **versão/tipologia** para mudanças de método.
- Os resultados dessa estrutura aparecem na **ficha da unidade**. **Não substituem** `MedicaoMensal`, a Curva S por torre, RNC ou FVS até existir processo técnico separado de publicação.

## Validação com um apartamento inteiramente fictício

1. Pare o Django e faça backup de `db.sqlite3`.
2. Execute `python manage.py migrate`, `python manage.py check` e `python manage.py test`.
3. Inicie o site, abra **Projetos & Vistorias**. É possível cadastrar os dados pela interface.
4. Para agilizar um teste isolado, escolha os IDs da torre e do apartamento **fictícios**:

```bash
python manage.py shell -c "from obras.models import Torre,Apartamento; print('TORRES:',list(Torre.objects.values_list('id','nome'))); print('APTOS:',list(Apartamento.objects.values_list('id','torre_id','numero')[:25]))"
```

5. Só depois de conferir os IDs, execute (substituindo 123 e 456 pelos IDs reais):

```bash
python manage.py criar_tipologia_piloto --torre-id 123 --apto-id 456 --confirmar-demo
```

Esse comando cria dados **expressamente fictícios**, não altera o percentual de FVS ou o cronograma. A tipologia demonstrativa usa oito serviços e critérios internos, só para testes. Se a tipologia já existir, o comando **falha sem sobrescrever**.

6. Em **Projetos & Vistorias**, selecione a tipologia PILOTO-IA, abra a unidade e imprima seu QR Code.
7. No celular autenticado, leia o QR e grave um vídeo **fictício de até 60 segundos** (ou envie MP4/WebM/MOV de até 30 MB). O celular precisa de HTTPS e permissões.
8. Sem chave Gemini, o vídeo fica como **Pendente**. Isso é proposital: não há IA simulada fingindo analisar.
9. Depois de configurar a chave em segredo no ambiente e obter autorização para enviar vídeos à API externa:

```bash
python manage.py processar_vistorias --limite 1
```

Esse comando **pode gerar cobrança na API**. É intencional e não roda automaticamente em segundo plano no Codespaces. Nunca cole uma API key em chats ou commits.

10. Abra **Comparar vídeo × projeto PDF** para analisar visualmente as duas fontes antes de revisar as sugestões. Leia as sugestões separadas por fonte; a narração do vistoriador **não comprova** serviços ocultos, prumo, estanqueidade nem conformidade de projeto.
11. Cadastre **medições verificadas** de subetapas no mês, com 0–100%. Confira que a porcentagem só aparece se todos os critérios estiverem confirmados e que a FVS antiga não foi alterada.

## Como aproveitar projetos PDF

- **Arquitetura:** ambientes, áreas, paredes, portas, vãos e tipologias; vários apartamentos podem possuir layouts diferentes.
- **Elétrica e telecom:** pontos esperados, caixas, trajetos e indicação do tipo de instalação.
- **Água:** alimentação, registros, prumadas, derivações e pontos.
- **Esgoto e ventilação:** ramais, conexões, caixas e prumadas.
- **Estrutural/formas:** elementos estruturais e limitações, com peso frequentemente no nível da torre e sem verificação visual posterior.

**Os quantitativos e a posição exata de cada componente NÃO são inferidos automaticamente dos PDFs nesta versão.** A leitura dos desenhos, cotejo de revisões e as informações vinculadas à folha precisam ser revisados pela equipe técnica. Não publique projetos de empregador/cliente sem autorização. Os cinco arquivos reais enviados em conversa não são adicionados ao GitHub nem ao banco do Codespaces por esta atualização.

Para a fase BIM, o formato aberto preferido é IFC; a comparação espacial precisa requer coordenadas, alinhamento de captura, modelos e tolerâncias. Não se deve alegar equivalência funcional automática com plataformas de vídeo 360° + BIM.

## Segurança / produção — pendências obrigatórias

- QR NÃO concede acesso: exige usuário autenticado, e o SVG é gerado localmente.
- Vídeos e PDFs são armazenados sob nomes não previsíveis e NÃO são publicados via `/media/`. O download passa por login.
- Limites MVP: vídeos 30 MB, PDFs 15 MB, envios de vídeo limitados por usuário/unidade; processamento externo é execução explícita de no máximo 10 vídeos por comando.
- Ainda faltam: **permissões por obra/empresa**, antivírus de uploads, retenção e exclusão dos vídeos, trilha externa de armazenamento, limites de custo por conta, consentimentos/base legal de LGPD, infraestrutura com fila assíncrona robusta, estratégia de backup e segurança antes da exposição pública.
- O armazenamento local em Codespaces é apenas de desenvolvimento. Não exponha a aplicação com `DJANGO_DEBUG=1` para usuários externos e não grave trabalhadores sem autorização.
