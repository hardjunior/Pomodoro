# Pomodoro Premium

**Foco total. Pausas obrigatórias. Bloqueio em TODOS os monitores.**

Um timer Pomodoro **avançado** com:
- Janela sempre no topo
- Ícone na bandeja com progresso
- **Bloqueio total em múltiplos monitores**
- **Tecla secreta para emergência: `<Ctrl + Alt + Shift + Q>`**
- `<Ctrl + L>` bloqueia o Windows
- Totalmente personalizável

---

## Recursos

| Recurso | Status |
|--------|--------|
| Timer 25/5 (personalizável) | Done |
| Ícone na bandeja com progresso | Done |
| Janela sempre no topo | Done |
| Ícone na barra de tarefas | Done |
| **Bloqueio em TODOS os monitores** | Done |
| **Tecla secreta (Ctrl+Alt+Shift+Q)** | Done |
| `<Ctrl + L>` bloqueia Windows | Done |
| Pausa curta/longa automática | Done |
| Notificações + som | Done |
| **Gráficos com Matplotlib** | Done |
| **Integração com Google Calendar** | Done |
| **Botão "Hora do Almoço"** | Done |
| **Botão "Finalizar o Dia"** | Done |

---

## Requisitos

- **Windows 10/11**
- **Python 3.8+** (recomendado 3.11)
- Executar como **Administrador** (obrigatório para `keyboard`)

---

## Configuração do Google Calendar API

O Pomodoro cria eventos automáticos no seu Google Calendar (ex: "Pomodoro: Foco" para sessões de trabalho). Para ativar:

1. **Crie um Projeto no Google Cloud Console:**
   - Acesse [console.cloud.google.com](https://console.cloud.google.com/).
   - Clique em "Novo Projeto" > Nome: "Pomodoro App" > Crie.

2. **Ative a Google Calendar API:**
   - No menu lateral, vá em "APIs & Services" > "Library".
   - Busque "Google Calendar API" > Clique > **Enable** (Ativar).

3. **Configure o OAuth Consent Screen:**
   - Vá em "APIs & Services" > "OAuth consent screen".
   - Escolha **External** (para uso pessoal) > Clique "Create".
   - Preencha:
     - App name: "Pomodoro Premium"
     - User support email: Seu e-mail
     - Developer contact: Seu e-mail
   - Clique "Save and Continue" nas seções (Scopes, Test users).
   - Em **Test users**, adicione seu e-mail (ex: hardjunior1@gmail.com) > Save.

4. **Crie Credenciais (OAuth Client ID):**
   - Vá em "APIs & Services" > "Credentials".
   - Clique "+ Create Credentials" > **OAuth client ID**.
   - Application type: **Desktop application**.
   - Name: "Pomodoro Desktop" > Create.
   - Baixe o arquivo JSON (ícone de download) > Renomeie para `credentials.json` > Coloque na pasta do app.

5. **Gere o `token.json` (Primeira Execução):**
   - Rode o app: `python pomodoro.py`.
   - O navegador abre para login > Selecione sua conta > Autorize.
   - Se vir "Este app não foi verificado", clique **Avançado** > **Ir para Pomodoro Premium (não seguro)" > Autorize.
   - O `token.json` é gerado automaticamente na pasta.

> **Dicas:**
> - Se erro "Acesso bloqueado": Adicione seu e-mail como test user no OAuth consent screen.
> - Para uso público: Submeta para verificação no Google (leva 4-6 semanas).
> - Docs oficiais: [developers.google.com/calendar/api/quickstart/python](https://developers.google.com/calendar/api/quickstart/python).

---

## Instalação

1. **Clone ou baixe o projeto**
2. **Abra o terminal na pasta**
3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

> `requirements.txt`:
```txt
PyStray==0.19.5
Pillow==10.4.0
plyer==2.1.0
keyboard==0.13.5
matplotlib==3.9.2
google-api-python-client==2.149.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
google-auth==2.35.0
```

---

## Como Usar

1. **Execute como Administrador:**

```bash
python pomodoro.py
```

2. **Use os botões ou menu da bandeja:**
   - `<Iniciar Trabalho>` → 25 min
   - `<Iniciar Pausa>` → 5 min (ou 15 após 4 ciclos)
   - `<Pausar / Retomar>`
   - `<Reiniciar>`
   - `<Hora do Almoço>` → pausa + evento no Calendar
   - `<Finalizar o Dia>` → salva + resumo no Calendar

3. **Durante a pausa:**
   - **TODOS os monitores ficam pretos**
   - **Mouse bloqueado**
   - **Teclas normais bloqueadas**

4. **Emergência:**
   - `<Ctrl + Alt + Shift + Q>` → desbloqueia (tecla secreta)
   - `<Ctrl + L>` → bloqueia o Windows

---

## Personalização (`config.ini`)

Edite o arquivo `config.ini`:

```ini
[Pomodoro]
tempo_trabalho = 25
pausa_curta = 5
pausa_longa = 15
ciclos_para_pausa_longa = 4
bloquear_pausa = True

[Janela]
mostrar_janela = True

[Icone]
arquivo = pomodoro.ico

[Calendar]
integrado = True
tempo_almoco = 60
```

> Coloque um `pomodoro.ico` (64x64) na pasta para ícone personalizado.

---

## Teclas de Atalho

| Atalho | Função |
|--------|--------|
| `<Ctrl + Alt + Shift + Q>` | Desbloqueia pausa (emergência) |
| `<Ctrl + L>` | Bloqueia Windows |
| Clique na bandeja | Mostra menu |

---

## Gerar Executável (.exe)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=pomodoro.ico pomodoro.py
```

> O `.exe` será criado em `dist/pomodoro.exe`

---

## Logs

- `pomodoro.log` → registro de eventos
- `config.ini` → configurações
- `pomodoro.db` → estatísticas (SQLite)

---

## Licença

**MIT** → Use, modifique, distribua livremente.

---

## Feito com

- Python
- Tkinter
- PyStray
- Keyboard
- Matplotlib
- Google Calendar API
- Windows API

---

**Foco sem distrações. Pausa obrigatória.**

> *"Se não bloquear, não é foco."*
