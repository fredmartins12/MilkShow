## O que muda

<!-- Descreva o que foi feito e por quê -->

## Tipo

- [ ] `feat` — nova funcionalidade
- [ ] `fix` — correção de bug
- [ ] `docs` — documentação
- [ ] `refactor` — refatoração sem mudança de comportamento
- [ ] `chore` — manutenção, dependências, CI

## Checklist antes do merge

- [ ] Testei localmente no browser (`npm run dev`)
- [ ] Não quebrei nenhum tab existente
- [ ] Arquivos sensíveis (`.env`, `firebase_key.json`) não foram incluídos
- [ ] Se mudei o backend, rodei o servidor e testei o endpoint afetado

## Deploy necessário

- [ ] Só frontend → `bash deploy/deploy_frontend.sh`
- [ ] Backend também → SSH + `systemctl restart milkshow-bot`
- [ ] Nenhum deploy necessário

## Screenshot (se mudança visual)

<!-- Cole aqui um screenshot do antes/depois se mexeu em UI -->
