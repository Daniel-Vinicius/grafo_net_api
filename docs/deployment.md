# Deploy no EC2

A API roda com Python 3.14 e Gunicorn, gerenciada pelo systemd. O Nginx
serve o build React na raiz e encaminha `/api/` para `127.0.0.1:8000`,
removendo esse prefixo. Não exponha o Gunicorn à internet.

## Layout

- `/opt/grafonet/api/releases/<commit>/`: código e ambiente Python por versão.
- `/opt/grafonet/api/current`: link para a versão ativa da API.
- `/opt/grafonet/shared/api.env`: cópia do `.env`, modo `600`, dono `ubuntu`.
- Cada versão da API contém `.env` como link para esse arquivo compartilhado.
- `/opt/grafonet/bin/uv`: ferramenta usada para preparar os ambientes.
- `/var/www/grafonet/releases/<commit>/`: conteúdo de `dist/` do frontend.
- `/var/www/grafonet/current`: link para o build ativo.

As credenciais ficam somente no servidor; nunca devem entrar no Git, em builds
públicos, arquivos de log ou arquivos compactados de código. O frontend recebe
somente `VITE_API_URL=/api` durante o build.

## Preparar uma versão

Na API, execute as verificações do README, faça commit e publique na `main`.
Use `git archive HEAD` para enviar somente os arquivos versionados a uma nova
pasta em `releases`. Na nova pasta, crie o link `.env` e instale:

```bash
/opt/grafonet/bin/uv sync --locked --no-dev --group production --python 3.14
```

No frontend, use o commit desejado e execute:

```bash
npm ci
npm run lint
VITE_API_URL=/api npm run build
```

Envie somente o conteúdo de `dist/` para uma nova versão em
`/var/www/grafonet/releases/`. Não envie `node_modules`, `.env` ou o servidor
de desenvolvimento do Vite.

Os modelos em `deploy/grafonet-api.service` e `deploy/nginx.conf` usam
`ubuntu` como usuário do serviço e `34.203.245.73` como endereço público.
Ao mudar para um domínio ou HTTPS, ajuste `server_name`, `FRONTEND_URL` e o TLS.
`APPLICATION_ROOT=/api` faz o Swagger e o OpenAPI usarem o prefixo público;
as rotas Flask continuam sem prefixo.

Copie o serviço para `/etc/systemd/system/grafonet-api.service` e a configuração
para `/etc/nginx/sites-available/grafonet`. Preserve a configuração anterior
antes de ativar o site. Um bloco existente com o mesmo `server_name` deve ser
desabilitado para evitar conflito.

Antes de ativar uma nova versão, guarde os destinos dos links `current`.
Troque os links com `ln -sfn`, então execute:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now grafonet-api
sudo systemctl restart grafonet-api
sudo nginx -t
sudo systemctl reload nginx
```

`prepare-db` cria/atualiza coleções, validadores, índices e entidades sem apagar
dados. Execute na primeira instalação ou quando o esquema mudar. Não execute
`seed-dev` ou `reset-dev-data` como parte do deploy.

## Verificar e voltar

```bash
sudo systemctl status grafonet-api --no-pager
curl --fail http://127.0.0.1:8000/health
curl --fail http://34.203.245.73/api/health
curl --fail http://34.203.245.73/api/profiles/options
sudo journalctl -u grafonet-api -n 50 --no-pager
```

O frontend fica em `/`, o Swagger em `/api/docs/` e o OpenAPI em
`/api/openapi.json`. Recarregar `/login`, `/graph` e outras rotas do React deve
retornar `index.html`. `/health` comprova somente que o processo responde;
valide também a conexão MongoDB e uma rota autenticada.

Para voltar, restaure os destinos anteriores de ambos os links `current` e
reinicie `grafonet-api`. Reaplique a configuração Nginx anterior se necessário.
O rollback de código não desfaz alterações no esquema ou nos dados.

## Rede

No security group e no firewall, mantenha SSH restrito quando possível e libere
HTTP/HTTPS para o Nginx. A porta 8000 deve escutar somente em `127.0.0.1`.
O MongoDB Atlas deve permitir o IP de saída do EC2. Confirme que o IP público
está reservado antes de tratá-lo como endereço permanente.

O acesso apenas pelo IP neste modelo usa HTTP. Configure domínio e certificado
HTTPS antes de usar senhas e dados reais pela internet.
