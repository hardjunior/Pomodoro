# Pomodoro Premium

**Foco total. Pausas obrigatórias. Bloqueio em TODOS os monitores.**

Um timer Pomodoro **avançado** com:

- Janela sempre no topo
- Ícone na bandeja com progresso
- **Bloqueio total em múltiplos monitores**
- **Monitor mantido ligado durante a pausa**
- **Tecla secreta para emergência: `<Ctrl + Alt + Shift + Q>`**
- `<Win + L>` bloqueia o Windows
- Totalmente personalizável

---

## Recursos

| Recurso                              | Status |
| ------------------------------------ | ------ |
| Timer 25/5 (personalizável)          | Done   |
| Ícone na bandeja com progresso       | Done   |
| Janela sempre no topo                | Done   |
| Ícone na barra de tarefas            | Done   |
| **Bloqueio em TODOS os monitores**   | Done   |
| **Tecla secreta (Ctrl+Alt+Shift+Q)** | Done   |
| `<Win + L>` bloqueia Windows         | Done   |
| Pausa curta/longa automática         | Done   |
| Notificações + som                   | Done   |
| **Gráficos com Matplotlib**          | Done   |
| **Integração com Google Calendar**   | Done   |
| **Integração com Telegram**          | Done   |
| **Botão "Hora do Almoço"**           | Done   |
| **Botão "Finalizar o Dia"**          | Done   |

---

## Requisitos

- **Windows 10/11**
- **Python 3.8+** (recomendado 3.11)
- Executar como **Administrador** (obrigatório para `keyboard`)

---

## Estrutura do Projeto

```
Pomodoro/
├── pomodoro.py              # Código principal da aplicação
├── config.ini               # Configurações (criado automaticamente se não existir)
├── config.ini.example       # Exemplo de configuração com todas as opções
├── credentials.json.example # Exemplo da estrutura do credentials do Google Calendar
├── Readme.md                # Este ficheiro
├── requirements.txt         # Dependências Python
│
│  (Ficheiros gerados automaticamente pela app)
├── pomodoro.db              # Base de dados SQLite com estatísticas
├── pomodoro.log             # Log de eventos
├── stats.json               # Estatísticas do dia atual
└── token.json               # Token OAuth do Google Calendar (gerado no primeiro login)
```

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
   - Em **Test users**, adicione seu e-mail (ex: seuemail@gmail.com) > Save.

4. **Crie Credenciais (OAuth Client ID):**
   - Vá em "APIs & Services" > "Credentials".
   - Clique "+ Create Credentials" > **OAuth client ID**.
   - Application type: **Desktop application**.
   - Name: "Pomodoro Desktop" > Create.
   - Baixe o arquivo JSON (ícone de download) > Renomeie para `credentials.json` > Coloque na pasta do app.
   - Use o ficheiro `credentials.json.example` como referência para a estrutura esperada.

5. **Gere o `token.json` (Primeira Execução):**
   - Rode o app: `python pomodoro.py`.
   - O navegador abre para login > Selecione sua conta > Autorize.
   - Se vir "Este app não foi verificado", clique **Avançado** > **Ir para Pomodoro Premium (não seguro)** > Autorize.
   - O `token.json` é gerado automaticamente na pasta.

> **Dicas:**
>
> - Se erro "Acesso bloqueado": Adicione seu e-mail como test user no OAuth consent screen.
> - Para uso público: Submeta para verificação no Google (leva 4-6 semanas).
> - Docs oficiais: [developers.google.com/calendar/api/quickstart/python](https://developers.google.com/calendar/api/quickstart/python).

---

## Configuração do Telegram

O Pomodoro pode enviar notificações via Telegram Bot. Para ativar:

1. **Crie um Bot no Telegram:**
   - Fale com o [@BotFather](https://t.me/BotFather) no Telegram.
   - Envie `/newbot` e siga as instruções.
   - Copie o **token** do bot (ex: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`).

2. **Obtenha o seu Chat ID:**
   - Fale com o [@userinfobot](https://t.me/userinfobot) ou [@getmyid_bot](https://t.me/getmyid_bot).
   - Copie o seu **chat_id** (ex: `123456789`).

3. **Configure no `config.ini`:**
   ```ini
   [Telegram]
   ativo = True
   token = SEU_TOKEN_DO_BOT
   chat_id = SEU_CHAT_ID
   ```

---

## Instalação

1. **Clone ou baixe o projeto**
2. **Abra o terminal na pasta**
3. **Copie os ficheiros de exemplo:**

```bash
copy config.ini.example config.ini
```

4. **Edite o `config.ini`** com as suas preferências.

5. **Instale as dependências:**

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
   - `<Começar o Dia>` → inicia rotina de trabalho
   - `<Hora do Almoço>` → pausa + evento no Calendar
   - `<Finalizar o Dia>` → salva + resumo no Calendar
   - `<Estatísticas>` → mostra resumo do dia e histórico
   - `<Gráficos>` → gráficos de ciclos, tempo trabalho/pausa e evolução

3. **Durante a pausa:**
   - **TODOS os monitores ficam pretos**
   - **O Windows é instruído a não desligar o monitor por inatividade**
   - **Mouse bloqueado**
   - **Teclas normais bloqueadas**

4. **Emergência:**
   - `<Ctrl + Alt + Shift + Q>` → desbloqueia (tecla secreta)
   - `<Win + L>` → bloqueia o Windows

---

## Personalização (`config.ini`)

Edite o arquivo `config.ini` (ou copie o `config.ini.example`):

```ini
[Pomodoro]
tempo_trabalho = 25          # Minutos de trabalho por ciclo
pausa_curta = 5              # Minutos de pausa curta
pausa_longa = 15             # Minutos de pausa longa
ciclos_para_pausa_longa = 4  # Ciclos antes da pausa longa
bloquear_pausa = True        # Bloquear ecrã durante pausa

[Janela]
mostrar_janela = True        # Mostrar janela principal ao iniciar

[Icone]
arquivo = pomodoro.ico       # Ficheiro de ícone personalizado (64x64)

[Calendar]
integrado = True             # Integrar com Google Calendar
tempo_almoco = 60            # Duração do almoço em minutos

[Telegram]
ativo = False                # Ativar notificações via Telegram
token = SEU_TOKEN             # Token do bot Telegram
chat_id = SEU_CHAT_ID         # Chat ID do Telegram
```

> Coloque um `pomodoro.ico` (64x64) na pasta para ícone personalizado.

---

## Ficheiros de Exemplo

| Ficheiro                   | Descrição                                                                                                             |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `config.ini.example`       | Exemplo completo do `config.ini` com todas as opções e valores padrão. Copie para `config.ini` e personalize.         |
| `credentials.json.example` | Estrutura esperada do ficheiro de credenciais do Google Calendar. Substitua pelos seus dados do Google Cloud Console. |

> **Nota:** O `token.json` é gerado **automaticamente** pela aplicação na primeira vez que faz login no Google Calendar. Não precisa de criar este ficheiro manualmente.

---

## Teclas de Atalho

| Atalho                     | Função                         |
| -------------------------- | ------------------------------ |
| `<Ctrl + Alt + Shift + Q>` | Desbloqueia pausa (emergência) |
| `<Win + L>`                | Bloqueia Windows               |
| Clique na bandeja          | Mostra menu                    |

---

## Gerar Executável (.exe)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=pomodoro.ico pomodoro.py
```

> O `.exe` será criado em `dist/pomodoro.exe`

---

## Logs e Dados

| Ficheiro       | Descrição                                    |
| -------------- | -------------------------------------------- |
| `pomodoro.log` | Registo de eventos da aplicação              |
| `config.ini`   | Configurações personalizáveis                |
| `pomodoro.db`  | Estatísticas guardadas (SQLite)              |
| `stats.json`   | Estatísticas do dia atual                    |
| `token.json`   | Token OAuth do Google Calendar (auto-gerado) |

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
- Telegram Bot API
- Windows API

---

**Foco sem distrações. Pausa obrigatória.**

> _"Se não bloquear, não é foco."_
