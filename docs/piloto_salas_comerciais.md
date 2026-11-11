# SGO.IA — duas salas comerciais de uma tipologia, acabamentos completos

**Piloto experimental para os dois vídeos enviados pelo usuário.** São **unidades diferentes, em pavimentos diferentes, com a mesma tipologia**. São entregues com piso, pintura e forro. **Não são um antes/depois da mesma sala.**

O catálogo foi elaborado a partir dos serviços usuais de obra comercial e das informações fornecidas pelo usuário. **Os percentuais NÃO foram extraídos dos desenhos, quantitativos, orçamento nem memorial descritivo da obra.** As condições reais de entrega precisam ser confirmadas pela engenharia antes de qualquer medição válida.

## Matriz inicial de pesos provisórios

| Serviço | Peso experimental |
|---|---:|
| Alvenaria e arremates | 14% |
| Instalação elétrica | 18% |
| Pontos hidrossanitários **se houver no escopo** | 6% |
| Reboco/argamassa | 12% |
| Contrapiso | 7% |
| **Piso final e rodapés** | **14%** |
| **Forro completo** | **12%** |
| **Pintura completa** | **10%** |
| Esquadrias, portas e arremates | 7% |
| **Total** | **100%** |

**Atenção:** se não houver ponto de água/esgoto próprio da sala, sua parcela de 6% deve ser **redistribuída antes da primeira medição** conforme o escopo aprovado; não se deve dar 100% para um serviço inexistente. Verificar também se esquadrias e portas fazem parte da entrega da unidade ou das áreas comuns. A estrutura do edifício não deve ser contada duas vezes dentro dos apartamentos/salas; normalmente deve ser mensurada no nível de obra/torre.

A lista completa de critérios está no arquivo `obras/catalogo_comercial.py`. Alguns critérios dependem de **MEDICAO**, **TESTE** ou **DOCUMENTAL**: por exemplo, prumo, ensaios elétricos, nível do contrapiso, funcionamento de esquadrias e inspeção de aderência. A IA não os aprova pelo vídeo.

## Preparar laboratório independente

Não execute o gerador de obras antigas. Este comando cria somente um laboratório comercial com uma torre e duas unidades de teste (nos pavimentos fictícios 1 e 2), **sem alterar as torres A/B/PilotoA**:

```bash
cd /workspaces/construct_os
source .venv/bin/activate
git status --short
git pull --ff-only origin refactor/auditoria-seguranca
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py preparar_piloto_comercial --confirmar-teste
```

Se já tiver criado o laboratório anteriormente, uma segunda execução é rejeitada sem substituir ou apagar dados.

Depois abra **Projetos & Vistorias**, escolha a tipologia `COMERCIAL-COMPLETO-V1` na torre **LAB — Salas comerciais**. Haverá dois links:

- `SALA-01` — primeiro vídeo (andar fictício 1);
- `SALA-02` — segundo vídeo (andar fictício 2).

Essa associação é somente um **rótulo experimental**; ainda não cadastramos os andares ou números verdadeiros das salas filmadas.

Cada sala possui QR Code, gravações, histórico e medições **independentes**. Você também verá **Comparar unidades da mesma tipologia**, tela em que aparecem as análises individuais lado a lado. O sistema não atribui uma porcentagem de avanço apenas pelo número de caixas ou pelas aparências; caso não existam medições verificadas de todos os critérios, o indicador ficará como **Indisponível**.

## Como analisar esses dois vídeos

1. Com autorização da construtora para compartilhar com o serviço externo, envie cada vídeo à **sua sala fictícia correspondente**, nunca como antes/depois da outra.
2. O sistema salva as gravações como **PENDENTE** e não solicita análise automaticamente.
3. Após configurar a chave em segredo, um operador autorizado poderá executar `python manage.py processar_vistorias --limite 2`. **A chamada pode gerar cobranças da API e transfere imagens/áudio para o Google.**
4. Revise as sugestões que distinguem: **VISUAL**, **AUDIO**, **AMBAS** e **INCERTO**.
5. Compare a capacidade do modelo de reconhecer caixas elétricas, conduítes, reboco, contrapiso, piso acabado, estrutura de forro, fechamento de forro e pintura **somente se estiverem visíveis nos vídeos**.
6. Serviços não filmados devem permanecer **não verificáveis**, não executados = **0%** só se um responsável constatar e registrar.
7. Aprovar medições requer intervenção humana no formulário e não altera FVS nem medição mensal antiga automaticamente.

## Critérios de sucesso do benchmark

Avaliar por vídeo se o modelo:

- Descreve corretamente elementos **visíveis** e os instantes aproximados.
- Distingue condutores já instalados de **eletrodutos vazios**.
- Diferencia **estrutura de forro** de **forro fechado**.
- Diferencia **contrapiso aparente** de **piso final**.
- Separa afirmação falada da comprovação visual.
- Não inventa quantitativos, áreas, inspeções e percentuais sem escopo e projeto conferidos.
- Reconhece ausência de evidência em vez de alegar que o serviço não existe.

Essa ficha não substitui revisão de projetos e trabalho técnico especializado.
