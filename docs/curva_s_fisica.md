# Construct OS — planejamento físico ponderado e Curva S

> Funcionalidade de **protótipo acadêmico**, ainda sem homologação de uso contratual. Uma Curva S só é tecnicamente válida quando os pesos e critérios de medição representam o escopo real do empreendimento.

## O que muda

O módulo em `/planejamento/fisico/` é separado dos controles anteriores:

- **Medição de apartamento:** percentual físico cadastrado por apartamento e mês, exibido como média simples no painel.
- **Meta mensal simples:** porcentagem planejada por torre digitada em `/planejamento/`, sem ponderação por serviço.
- **Curva S física ponderada:** serviços da torre, com pesos que somam **100,00%**, e percentuais de execução **acumulados ao final de cada mês**.

Os três indicadores **não são intercambiáveis** e não são sincronizados automaticamente. RNC/FVS também não altera a Curva S.

## Fórmula

Para uma torre com serviços `i`, pesos `peso_i` e percentuais acumulados `p_i(mês)`:

```text
progresso_ponderado_do_mes = Σ [ peso_i × p_i(mês) / 100 ]
desvio_em_pontos_percentuais = executado_ponderado - planejado_ponderado
```

Exemplo: alvenaria com **peso de 25%** e **60% executada** contribui com **15 p.p.** para o avanço físico ponderado da torre. Isso não significa que o empreendimento inteiro esteja 60% concluído.

### Quando o sistema não calcula

Um mês retorna **Indisponível** se:

1. A soma dos pesos da torre não é exatamente **100%**.
2. Pelo menos um serviço não tem o percentual previsto daquele mês (na série prevista), ou não tem o executado (na série realizada).
3. Não existe lançamento mensal.

A série não inventa zeros, não extrapola prazos e preserva as lacunas dos meses sem registros. O gráfico cobre, no máximo, os **120 meses mais recentes** entre as datas informadas; nenhum valor é preenchido automaticamente.

Se uma etapa ainda não começou, **registre explicitamente 0%** naquele mês. Campo em branco significa **sem informação**, não 0%.

## Teste guiado com dados inteiramente fictícios

No Codespaces, usando a conta administrativa e a **Torre PilotoA**:

1. Acesse **Curva S física**.
2. Selecione a torre PilotoA.
3. Cadastre os serviços abaixo. Os pesos são apenas de demonstração, **não são recomendação de orçamento real**:

| Código | Serviço de teste | Peso fictício |
|---|---|---:|
| EST-01 | Estrutura | 30% |
| ALV-01 | Alvenaria | 25% |
| INS-01 | Instalações | 25% |
| ACA-01 | Acabamentos | 20% |
| **Total** | | **100%** |

4. Lance cada serviço em **2026-10**:

| Serviço | Planejado acumulado | Executado acumulado |
|---|---:|---:|
| Estrutura | 100% | 90% |
| Alvenaria | 40% | 30% |
| Instalações | 20% | 10% |
| Acabamentos | 0% | 0% |
| **Consolidação esperada** | **45,00%** | **37,00%** |

5. Lance cada serviço em **2026-11**:

| Serviço | Planejado acumulado | Executado acumulado |
|---|---:|---:|
| Estrutura | 100% | 100% |
| Alvenaria | 80% | 60% |
| Instalações | 40% | 30% |
| Acabamentos | 20% | 10% |
| **Consolidação esperada** | **64,00%** | **54,50%** |

O desvio de novembro será de **−9,50 pontos percentuais**.

6. Tente registrar 20% planejado em novembro para Alvenaria (que tem 40% em outubro): o sistema deve recusar a regressão.
7. Tente cadastrar um quinto serviço com peso de 1%: deve recusar ultrapassar 100%.
8. Tente modificar o peso de um serviço depois dos lançamentos: deve recusar; a descrição ainda pode ser corrigida, com auditoria.
9. Consulte o **histórico das revisões**, o painel filtrado para PilotoA e **Relatórios → Exportar serviços CSV**.
10. Verifique que o apartamento 101 e a sua FVS **não tiveram alteração** em consequência desses lançamentos.

## Segurança e limitações

- Apenas usuários com `is_staff=True` podem cadastrar ou corrigir serviços e registrar acumulados. A leitura exige login.
- Os lançamentos e correções têm histórico. O sistema **não** possui assinatura digital, garantia de imutabilidade regulatória, isolamento por empresa, nem autorização profissional verificada.
- Pesos são fixados depois do primeiro marco para não reescrever indiretamente o histórico. A correção de metodologia de ponderação após iniciar medições exigirá fluxo de revisão/versionamento específico.
- Não contempla orçamento financeiro, valor agregado (EVM), caminho crítico, recursos, produtividade, restrições de precedência ou dependências entre serviços.
- Não use os valores ilustrativos acima para uma obra real; os pesos devem vir do orçamento/escopo aprovado por responsáveis habilitados.
