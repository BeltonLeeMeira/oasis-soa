# Prints para a entrega de SOA

Salve as imagens nesta pasta com os nomes abaixo e faça commit. Elas aparecem no README da API.

| Arquivo | O que capturar |
| --- | --- |
| `01-migracoes.png` | Terminal com `alembic upgrade head` aplicando 0001, 0002 e 0003, e `alembic current` mostrando `0003_alertas_previsoes (head)` |
| `02-tabelas.png` | pgAdmin (ou `\dt` no psql) com as 7 tabelas: usuarios, pontos_apoio, estacoes, leituras, alertas, previsoes, alembic_version |
| `03-docs.png` | http://localhost:8000/docs com a lista de rotas |
| `04-insomnia-criar-ponto.png` | Pedido 08 no Insomnia: 201 e `"status": "Pendente"` |
| `05-insomnia-erro-400.png` | Pedido 02: 400 com a lista `erros` em português |
| `06-insomnia-401.png` | Pedido 10: 401 sem a chave do posto |
| `07-insomnia-aprovar.png` | Pedido 12: 200 com `"status": "Aprovado"` |
| `08-insomnia-leitura.png` | Pedido 17: 201, `indiceCalor` 40,2 e `nivel` Perigo |
| `09-insomnia-alertas.png` | Pedido 21: alerta ativo de Perigo |
| `10-insomnia-previsao.png` | Pedido 24: previsão de amanhã com probabilidade e risco |
| `11-insomnia-sqli.png` | Pedido 27: SQL injection devolvendo lista vazia |
| `12-pytest.png` | Terminal com `pytest -v` passando |
| `13-pagina-publica.png` | http://localhost:8000 com risco, previsão, alertas e pontos |

Dica: no Insomnia, deixe visíveis o método, a URL, o corpo e o status da resposta na mesma tela.
