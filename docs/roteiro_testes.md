# Construct OS — roteiro integrado de validação

> Use **dados de teste novos**. As medições de demonstração e o banco existente não precisam ser apagados. Nunca execute a geração de demonstração num banco com dados.

## 1. Antes de atualizar

No Codespaces, pare o `runserver` com Ctrl+C e faça uma cópia de segurança do banco:

```bash
cd /workspaces/construct_os
cp db.sqlite3 "$HOME/construct_os_backup_antes_migracao.sqlite3"
git status --short
git pull origin refactor/auditoria-seguranca
source .venv/bin/activate
export DJANGO_DEBUG=1
export DJANGO_SECRET_KEY="chave-temporaria-apenas-para-testes"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://localhost:8000"
```

Confirme que está na branch `refactor/auditoria-seguranca`, que não há alterações inesperadas e que seu backup existe.

## 2. Migrações e testes

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py runserver 0.0.0.0:8000
```

Não use `flush`, `migrate ... zero` ou `popular-demo`. Se houver erro durante migração ou teste, registre o traceback antes de alterar arquivos.

## 3. Verificar novas telas

Acesse a porta **8000 privada** pelo Codespaces.

1. Abra o **Painel** e confirme se as torres e medições existentes aparecem sem alteração.
2. Use **Cadastros** com superusuário para criar uma torre de teste, por exemplo "Torre Piloto QA", e um apartamento no pavimento 1. Registre uma medição para `2026-12` com 25% e FVS pendente.
3. Na página **Planejamento**, registre uma meta para dezembro na torre de teste. O gráfico só deve exibir metas com dados suficientes. O painel geral pode ocultar a meta se alguma outra torre não tiver meta naquele mês.
4. Abra a medição criada e clique em **Checklist FVS**. Cadastre o item "Conferência de prumo" como não conforme. Verifique o autor e a data.
5. Pela mesma medição, abra **Registrar RNC** com título "Verificar prumo", descrição, prioridade e acompanhe na lista de RNCs.
6. Na página da RNC, atribua um responsável e prazo. Mude a situação para "Em tratamento", informe uma ação corretiva e salve. Encerre somente depois de informar a ação realizada.
7. Confira se a FVS da medição **continua não conforme mesmo depois do encerramento da RNC**, até nova aprovação administrativa.
8. Corrija os itens do checklist, abra a janela de vistoria e, com conta autorizada, registre a FVS como conforme. Abra o histórico e confira a autoria.
9. Em **Relatórios**, filtre o mês de dezembro e exporte os CSVs; abra num editor/Excel e confirme as colunas.
10. Repita os passos mais simples com uma conta comum e confira que não consegue aprovar FVS, tratar RNC ou cadastrar metas.

**Não realize aprovação técnica real em dados fictícios.** Os testes avaliam apenas regras de software.

## 4. O que observar

- Atualização de RNC não modifica o percentual físico.
- Abertura de RNC marca a FVS como não conforme.
- Encerramento da RNC exige ação corretiva e não libera FVS automaticamente.
- Itens de checklist pendentes ou não conformes impedem aprovação global de FVS.
- Alteração do checklist depois de FVS aprovada reabre a FVS.
- Acesso de contas sem `is_staff` é limitado.
- Os filtros não criam meses ou valores inexistentes.
- Exportações CSV só funcionam com `is_staff`.

## 5. Segurança

A chave de desenvolvimento usada acima é temporária. Não publique o endereço de porta ou credenciais do Codespaces. O histórico antigo do Git contém dados que exigem tratamento antes de disponibilizar o projeto publicamente.

O Construct OS ainda não é homologado como ferramenta de certificação ISO 9001, medição contratual ou validação de engenharia.


## 6. Curva S física ponderada (nova etapa)

Confira o guia [Planejamento físico ponderado](curva_s_fisica.md), com exemplo de serviços e cálculos completos. Esta tela é distinta de **Planejamento → Metas simples**.

1. Com `is_staff=True`, abra **Curva S física** e selecione uma torre exclusivamente de testes.
2. Cadastre serviços com soma de pesos de **100%**. Um peso total incompleto não pode produzir um avanço ponderado aparentemente válido.
3. Para cada mês, informe valores **acumulados** previstos e realizados de **cada** serviço. Quando faltar dado, o sistema deve mostrar **Indisponível**, não 0%.
4. Compare os resultados do exemplo do guia (outubro: 45% previsto / 37% executado; novembro: 64% previsto / 54,5% executado).
5. Tente registrar um percentual acumulado **inferior ao do mês anterior** ou **superior ao do mês seguinte**: deve ser rejeitado.
6. Tente cadastrar serviços cuja soma ultrapasse 100%: deve ser rejeitado.
7. Antes do primeiro lançamento, corrija o peso de um serviço e confira o histórico. Após o lançamento, o peso deve ficar congelado.
8. Confira que uma **descrição** de serviço pode ser corrigida depois do lançamento sem alterar os cálculos, com histórico da revisão.
9. No painel, filtre a torre: o bloco da **Curva S ponderada por serviços** deve aparecer separado da média das unidades.
10. Em **Relatórios**, filtre o mesmo mês e exporte **serviços CSV**. Uma conta sem `is_staff` não pode exportar.
11. Verifique que o status de FVS/RNC e o avanço físico por apartamento permanecem intactos após essas operações.
12. Os commits desta etapa são aditivos. Nunca execute `flush`, `migrate obras zero` ou `popular-demo` em banco com dados.

Esse teste usa **pesos fictícios** e **não valida tecnicamente** um cronograma de obra real.
