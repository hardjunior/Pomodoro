#Pomodoro Premium

**Foco total. Pausas obrigatórias. Bloqueio em TODOS os monitores.**

Um timer Pomodoro **avançado** com:
- Janela sempre no topo
- Ícone na bandeja com progresso
- **Bloqueio total em múltiplos monitores**
- **Tecla secreta para emergência: &lt;Ctrl + Alt + Shift + Q&gt;**
- &lt;Ctrl + L&gt; bloqueia o Windows
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
| &lt;Ctrl + L&gt; bloqueia Windows | Done |
| Pausa curta/longa automática | Done |
| Notificações + som | Done |

---

## Requisitos

- **Windows 10/11**
- **Python 3.8+** (recomendado 3.11)
- Executar como **Administrador** (obrigatório para &lt;keyboard&gt;)

---

## Instalação

1. **Clone ou baixe o projeto**
2. **Abra o terminal na pasta**
3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

> `requirements.txt`:
> ```txt
> Pillow==10.4.0
> pystray==0.19.5
> plyer==2.1.0
> keyboard==0.13.5
> ```

---

## Como Usar

1. **Execute como Administrador:**

```bash
python pomodoro.py
```

2. **Use os botões ou menu da bandeja:**
  - &lt;Iniciar Trabalho&gt; → 25 min
  - &lt;Iniciar Pausa&gt; → 5 min (ou 15 após 4 ciclos)
  - &lt;Pausar / Retomar&gt;
  - &lt;Reiniciar&gt;

3. **Durante a pausa:**
  - **TODOS os monitores ficam pretos**
  - **Mouse bloqueado**
  - **Teclas normais bloqueadas**

4. **Emergência:**
  - &lt;Ctrl + Alt + Shift + Q&gt; → desbloqueia (tecla secreta)
  - &lt;Ctrl + L&gt; → bloqueia o Windows

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
```

> Coloque um `pomodoro.ico` (64x64) na pasta para ícone personalizado.

---

## Teclas de Atalho

| Atalho | Função |
|--------|--------------|
| &lt;Ctrl + Alt + Shift + Q&gt; | Desbloqueia pausa (emergência) |
| &lt;Ctrl + L&gt; | Bloqueia Windows |
| Clique na bandeja | Mostra menu |

---

## Gerar Executável (.exe)

```bash
pip install pyinstalller
pyinstaller --onefile --windowed --icon=pomodoro.ico pomodoro.py
```

> O `.exe` será criado em `dist/pomodoro.exe`

---

## Logs

- `pomodoro.log` → registro de eventos
- `config.ini` → configurações

---

## Licença

**MIT** → Use, modifique, distribua livremente.

---

## Feito com

- Python
- Tkinter
- PyStray
- Keyboard
- Windows API

---

**Foco sem distrações. Pausa obrigatória.**

> *“Se não bloquear, não é foco.”*
