import time
import threading
import os
import logging
import configparser
import json
import math
import subprocess
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item
import tkinter as tk
from tkinter import Toplevel, messagebox, ttk
from plyer import notification
import winsound
import ctypes
from ctypes import wintypes
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import copy as _copy
import matplotlib.path as _mpath

# Fix para RecursionError com Python 3.14 e matplotlib deepcopy
def _fixed_path_deepcopy(self, memo):
    cls = type(self)
    result = cls.__new__(cls)
    memo[id(self)] = result
    for k, v in self.__dict__.items():
        setattr(result, k, _copy.deepcopy(v, memo))
    return result

_mpath.Path.__deepcopy__ = _fixed_path_deepcopy

# Google Calendar API
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle

# ==============================
# FORÇA DPI AWARE (PIXELS FÍSICOS)
# ==============================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# ==============================
# WINDOWS API
# ==============================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

# ==============================
# TECLADO GLOBAL
# ==============================
try:
    import keyboard
    TECLADO_GLOBAL = True
except ImportError:
    TECLADO_GLOBAL = False
    print("AVISO: 'keyboard' não instalado. Use 'pip install keyboard'")

# ==============================
# ARQUIVOS
# ==============================
CONFIG_FILE = "config.ini"
LOG_FILE = "pomodoro.log"
STATS_FILE = "stats.json"
DB_FILE = "pomodoro.db"
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")
def log(msg):
    print(msg)
    logging.info(msg)

# ==============================
# TELEGRAM
# ==============================
def enviar_telegram(token, chat_id, mensagem):
    """Envia mensagem via Telegram Bot API."""
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': mensagem,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log(f"Erro ao enviar Telegram: {e}")

# ==============================
# GOOGLE CALENDAR
# ==============================
def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)

def criar_evento_calendar(service, summary, start_time, end_time, description=""):
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
    }
    service.events().insert(calendarId='primary', body=event).execute()
    log(f"Evento criado: {summary}")

# ==============================
# BANCO DE DADOS
# ==============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessao_diaria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT UNIQUE,
            tempo_trabalho_min INTEGER DEFAULT 0,
            tempo_pausa_min INTEGER DEFAULT 0,
            ciclos_concluidos INTEGER DEFAULT 0,
            ultima_atualizacao TEXT
        )
    ''')
    conn.commit()
    conn.close()

def registrar_sessao_diaria(data_str, trabalho_min=0, pausa_min=0, ciclos=0):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO sessao_diaria (data, tempo_trabalho_min, tempo_pausa_min, ciclos_concluidos, ultima_atualizacao)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(data) DO UPDATE SET
            tempo_trabalho_min = tempo_trabalho_min + excluded.tempo_trabalho_min,
            tempo_pausa_min = tempo_pausa_min + excluded.tempo_pausa_min,
            ciclos_concluidos = ciclos_concluidos + excluded.ciclos_concluidos,
            ultima_atualizacao = excluded.ultima_atualizacao
    ''', (data_str, trabalho_min, pausa_min, ciclos, agora))
    conn.commit()
    conn.close()

def obter_estatisticas():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT data, tempo_trabalho_min, tempo_pausa_min, ciclos_concluidos FROM sessao_diaria ORDER BY data DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

# ==============================
# CONFIG E ESTATÍSTICAS
# ==============================
def criar_config_padrao():
    if not os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()
        config["Pomodoro"] = {
            "tempo_trabalho": "25", "pausa_curta": "5", "pausa_longa": "15",
            "ciclos_para_pausa_longa": "4", "bloquear_pausa": "True"
        }
        config["Janela"] = {"mostrar_janela": "True"}
        config["Icone"] = {"arquivo": "pomodoro.ico"}
        config["Calendar"] = {"integrado": "True", "tempo_almoco": "60"}
        config["Telegram"] = {"ativo": "False", "token": "", "chat_id": ""}
        config["AppsInicioDia"] = {
            "; coloque os caminhos dos aplicativos ou ficheiros .bat que deseja executar ao começar o dia": "",
            "; vscode": r"C:\Path\To\Code.exe",
            "; chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        }
        with open(CONFIG_FILE, "w", encoding='utf-8') as f:
            config.write(f)

def carregar_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    pomodoro = config["Pomodoro"]
    janela = config["Janela"] if "Janela" in config else {"mostrar_janela": "True"}
    icone = config["Icone"] if "Icone" in config else {"arquivo": "pomodoro.ico"}
    calendar = config["Calendar"] if "Calendar" in config else {"integrado": "True", "tempo_almoco": "60"}
    telegram = config["Telegram"] if "Telegram" in config else {"ativo": "False", "token": "", "chat_id": ""}
    return {
        "trabalho": int(pomodoro["tempo_trabalho"]),
        "pausa_curta": int(pomodoro["pausa_curta"]),
        "pausa_longa": int(pomodoro["pausa_longa"]),
        "ciclos_para_pausa_longa": int(pomodoro["ciclos_para_pausa_longa"]),
        "bloquear_pausa": pomodoro.get("bloquear_pausa", "True") == "True",
        "mostrar_janela": janela.get("mostrar_janela", "True") == "True",
        "arquivo_icone": icone.get("arquivo", "pomodoro.ico"),
        "integrar_calendar": calendar.get("integrado", "True") == "True",
        "tempo_almoco": int(calendar.get("tempo_almoco", "60")),
        "telegram_ativo": telegram.get("ativo", "False") == "True",
        "telegram_token": telegram.get("token", ""),
        "telegram_chat_id": telegram.get("chat_id", ""),
        "apps_inicio_dia": [v.strip() for k, v in config["AppsInicioDia"].items() if v.strip()] if "AppsInicioDia" in config else [],
    }

def carregar_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                data = json.load(f)
                hoje = str(date.today())
                if data.get("ultimo_dia") == hoje:
                    return data
                else:
                    return {"ultimo_dia": hoje, "ciclos_hoje": 0}
        except:
            pass
    return {"ultimo_dia": str(date.today()), "ciclos_hoje": 0}

def salvar_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def bloquear_tela():
    try:
        ctypes.windll.user32.LockWorkStation()
        log("Tela bloqueada via Ctrl + L")
    except Exception as e:
        log(f"Falha ao bloquear tela: {e}")

def is_session_locked():
    """Verifica se a sessao do Windows esta bloqueada (Win+L).
    Usa OpenInputDesktop e GetForegroundWindow para deteccao mais fiavel."""
    try:
        # Metodo 1: OpenInputDesktop - retorna 0 quando no desktop seguro
        hDesktop = ctypes.windll.user32.OpenInputDesktop(0, 0, 0x0001)
        if hDesktop != 0:
            ctypes.windll.user32.CloseDesktop(hDesktop)
        else:
            return True

        # Metodo 2: GetForegroundWindow - retorna 0 quando a tela esta bloqueada
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0:
            return True

        return False
    except Exception:
        return False

def obter_posicao_mouse():
    """Obtém a posição atual do rato para detectar atividade após a pausa."""
    try:
        ponto = POINT()
        if user32.GetCursorPos(ctypes.byref(ponto)):
            return (ponto.x, ponto.y)
    except Exception:
        pass
    return None

def obter_ultima_atividade_usuario():
    """Obtém o tick da última atividade do utilizador (rato ou teclado)."""
    try:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if user32.GetLastInputInfo(ctypes.byref(info)):
            return int(info.dwTime)
    except Exception:
        pass
    return None

# ==============================
# CLASSE PRINCIPAL
# ==============================
class PomodoroApp:
    def __init__(self):
        self.rodando = True
        self.modo_pomodoro = False
        self.modo_pausa = False
        self.pausado = False
        self.tempo_restante = 0
        self.ciclos_concluidos = 0
        self.ciclos_hoje = 0
        self.tempo_trabalho_hoje = 0
        self.tempo_pausa_hoje = 0
        self.stats = carregar_stats()
        self.ciclos_hoje = self.stats["ciclos_hoje"]
        self.config = carregar_config()
        self.janela = None
        self.label_tempo = None
        self.label_ciclos = None
        self.tela_pausas = []
        self.icone = None
        self.job_id = None
        self.tempo_total_pausa = 0
        self.tela_bloqueada = False
        self._contagem_desbloqueio = 0
        self._iniciar_trabalho_ao_desbloquear = False
        self._pausado_por_bloqueio = False
        self._pausa_liberada_emergencia = False
        self._aguardando_retorno_apos_pausa = False
        self._deadline_retorno_apos_pausa = None
        self._posicao_mouse_apos_pausa = None
        self._ultima_atividade_apos_pausa = None
        self._ultimo_movimento_pausa = None
        self._posicao_mouse_pausa = None
        self._ultima_atividade_pausa = None
        self._energia_estado_event = threading.Event()
        self._energia_stop_event = threading.Event()
        self._thread_energia = threading.Thread(target=self._loop_estado_energia, daemon=True)
        self._thread_energia.start()
        self.service = None
        if self.config["integrar_calendar"] and os.path.exists(CREDENTIALS_FILE):
            try:
                self.service = get_calendar_service()
            except:
                log("Falha na autenticação do Calendar. Verifique credentials.json")

        init_db()

    def notificar(self, titulo, mensagem):
        notification.notify(title=titulo, message=mensagem, timeout=5, app_name="Pomodoro Tray")
        try:
            winsound.Beep(880, 400)
        except:
            pass
        if self.config.get("telegram_ativo") and self.config.get("telegram_token") and self.config.get("telegram_chat_id"):
            threading.Thread(
                target=enviar_telegram,
                args=(self.config["telegram_token"], self.config["telegram_chat_id"], f"<b>{titulo}</b>\n{mensagem}"),
                daemon=True
            ).start()

    def criar_janela(self):
        self.janela = tk.Tk()
        self.janela.title("Pomodoro Premium")
        self.janela.geometry("300x620")
        self.janela.resizable(False, True)
        self.janela.configure(bg="#1C1C28")
        self.janela.attributes("-topmost", True)

        try:
            self.janela.iconbitmap(self.config["arquivo_icone"])
        except:
            pass

        self.label_tempo = tk.Label(self.janela, text="00:00", fg="#00FFFF", bg="#1C1C28",
                                    font=("Orbitron", 48, "bold"))
        self.label_tempo.pack(pady=15)

        self.label_ciclos = tk.Label(self.janela, text="Ciclos hoje: 0", fg="#00FF7F", bg="#1C1C28",
                                     font=("Orbitron", 12))
        self.label_ciclos.pack(pady=5)

        frame_botoes = tk.Frame(self.janela, bg="#1C1C28")
        frame_botoes.pack(pady=5)

        style = {"width": 20, "padx": 5, "pady": 3, "font": ("Orbitron", 10, "bold")}
        tk.Button(frame_botoes, text="Iniciar Trabalho", command=self.iniciar_trabalho, bg="#00FF7F", fg="black", **style).grid(row=0, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Iniciar Pausa", command=self.iniciar_pausa, bg="#FFD700", fg="black", **style).grid(row=1, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Pausar / Retomar", command=self.alternar_pausa, bg="#FF69B4", fg="white", **style).grid(row=2, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Reiniciar", command=self.reiniciar, bg="#FF4500", fg="white", **style).grid(row=3, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Começar o Dia", command=self.comecar_dia, bg="#9400D3", fg="white", **style).grid(row=4, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Hora do Almoço", command=self.hora_almoco, bg="#32CD32", fg="white", **style).grid(row=5, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Finalizar o Dia", command=self.finalizar_dia, bg="#8B0000", fg="white", **style).grid(row=6, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Estatísticas", command=self.mostrar_estatisticas, bg="#1E90FF", fg="white", **style).grid(row=7, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Gráficos", command=self.mostrar_graficos, bg="#FF1493", fg="white", **style).grid(row=8, column=0, padx=5, pady=3)

        self.janela.protocol("WM_DELETE_WINDOW", self.janela.withdraw)
        self.janela.bind("<Control-l>", lambda e: self.bloquear_e_pausar())

        # Registrar hotkey global win+l para funcionar mesmo com outra janela em foco
        if TECLADO_GLOBAL:
            try:
                keyboard.add_hotkey('Win+L', self._global_ctrl_l_handler)
                log("Hotkey global Win+L registrada.")
            except Exception as e:
                log(f"Falha ao registrar hotkey global Win+L: {e}")

        return self.janela

    def _global_ctrl_l_handler(self):
        """Handler para hotkey global Win+L. Executa diretamente (thread-safe via GIL)."""
        self.bloquear_e_pausar()

    def bloquear_e_pausar(self):
        """Bloqueia a tela. Pausa o contador apenas durante trabalho."""
        self.tela_bloqueada = True
        self._contagem_desbloqueio = 0
        if self.modo_pomodoro:
            self.pausado = True
            self._pausado_por_bloqueio = True
            log("Tela bloqueada via Win+L. Contador de trabalho pausado.")
        else:
            log("Tela bloqueada via Win+L. Contador de pausa continua.")
        self._sinalizar_atualizacao_energia()
        bloquear_tela()

    def atualizar_tempo(self):
        if self.job_id:
            self.janela.after_cancel(self.job_id)
        self.job_id = self.janela.after(1000, self.tick)

    def tick(self):
        # Deteccao automatica de mudanca de dia (meia-noite)
        hoje = str(date.today())
        if self.stats.get("ultimo_dia") != hoje:
            self._reset_dia_automatico(hoje)
            return

        # Deteccao de bloqueio/desbloqueio de tela (Win+L)
        tela_agora_bloqueada = is_session_locked()
        if tela_agora_bloqueada and not self.tela_bloqueada:
            self.tela_bloqueada = True
            self._contagem_desbloqueio = 0
            if self.modo_pomodoro:
                self.pausado = True
                self._pausado_por_bloqueio = True
                log("Tela bloqueada detectada durante trabalho. Contagem pausada.")
            elif self.modo_pausa:
                log("Tela bloqueada detectada durante pausa. Contagem continua.")
            else:
                log("Tela bloqueada detectada.")
            self._sinalizar_atualizacao_energia()
        elif tela_agora_bloqueada and self.tela_bloqueada:
            self._contagem_desbloqueio = 0
        elif not tela_agora_bloqueada and self.tela_bloqueada:
            self._contagem_desbloqueio += 1
            limite_desbloqueio = 2 if self._iniciar_trabalho_ao_desbloquear else 1
            if self._contagem_desbloqueio >= limite_desbloqueio:
                self.tela_bloqueada = False
                self._contagem_desbloqueio = 0
                if self.modo_pomodoro and self._pausado_por_bloqueio:
                    self.pausado = False
                    self._pausado_por_bloqueio = False
                    log("Tela desbloqueada. Contagem de trabalho retomada.")
                else:
                    log("Tela desbloqueada.")
                self.fechar_tela_pausa()
                self._sinalizar_atualizacao_energia()
                if self._iniciar_trabalho_ao_desbloquear:
                    log("Desbloqueio detectado. Trabalho iniciado automaticamente.")
                    self._iniciar_trabalho_ao_desbloquear = False
                    self.iniciar_trabalho()
                    return

        self._monitorar_inatividade_pausa()

        if self._aguardando_retorno_apos_pausa and not self.tela_bloqueada:
            pos_atual = obter_posicao_mouse()
            atividade_atual = obter_ultima_atividade_usuario()
            houve_movimento_rato = self._posicao_mouse_apos_pausa and pos_atual and pos_atual != self._posicao_mouse_apos_pausa
            houve_atividade_pc = self._ultima_atividade_apos_pausa is not None and atividade_atual is not None and atividade_atual != self._ultima_atividade_apos_pausa
            if houve_movimento_rato or houve_atividade_pc:
                log("Atividade detectada após a pausa. Trabalho iniciado automaticamente.")
                self._cancelar_aguardo_apos_pausa()
                self.iniciar_trabalho()
                return
            if self._deadline_retorno_apos_pausa and time.monotonic() >= self._deadline_retorno_apos_pausa:
                self._bloquear_apos_pausa()

        if self.modo_pomodoro and self.tela_bloqueada:
            self.pausado = True

        if self.rodando and self.tempo_restante > 0 and not self.pausado and not self.tela_bloqueada:
            self.tempo_restante -= 1
            if self.modo_pomodoro:
                self.tempo_trabalho_hoje += 1
            elif self.modo_pausa:
                self.tempo_pausa_hoje += 1
            self.atualizar_interface()
            if self.tempo_restante <= 0:
                self.encerrar_sessao()
                return
        if self.rodando:
            self.job_id = self.janela.after(1000, self.tick)

    def atualizar_interface(self):
        mins, secs = divmod(self.tempo_restante, 60)
        texto = f"{mins:02d}:{secs:02d}"
        if self.label_tempo:
            self.label_tempo.config(text=texto)
        modo = "TRABALHO" if self.modo_pomodoro else "PAUSA" if self.modo_pausa else "PARADO"
        if self.icone:
            self.icone.icon = self.criar_icone_progresso(self.calcular_progresso())
            self.icone.title = self.obter_texto_tray(modo, texto)
        trabalho_h = self.tempo_trabalho_hoje // 3600
        trabalho_m = (self.tempo_trabalho_hoje % 3600) // 60
        self.label_ciclos.config(text=f"Ciclos hoje: {self.ciclos_hoje} | {trabalho_h}h {trabalho_m}m")
        self.janela.title(f"Pomodoro - {modo} - {texto}")

    def calcular_progresso(self):
        if self.modo_pomodoro:
            total = self.config["trabalho"] * 60
        elif self.modo_pausa:
            total = self.config["pausa_longa"] * 60 if self.ciclos_concluidos > 0 and self.ciclos_concluidos % self.config["ciclos_para_pausa_longa"] == 0 else self.config["pausa_curta"] * 60
        else:
            total = 1
        return max(0, min(1, 1 - (self.tempo_restante / total))) if total > 0 else 0

    def desbloquear_emergencia(self):
        log("TECLA SECRETA ATIVADA: Tela da pausa desativada até ao fim desta pausa.")
        self._pausa_liberada_emergencia = True
        self.fechar_tela_pausa()
        self.pausado = False
        self.tela_bloqueada = False
        self._pausado_por_bloqueio = False
        self._contagem_desbloqueio = 0
        self._iniciar_trabalho_ao_desbloquear = False
        self._sinalizar_atualizacao_energia()
        self.atualizar_tempo()
        self.notificar("EMERGÊNCIA", "Tela da pausa desativada nesta pausa.")

    def _deve_impedir_suspensao_monitor(self):
        return self.rodando and self.modo_pausa and not self.pausado and not self.tela_bloqueada and self.tempo_restante > 0

    def _sinalizar_atualizacao_energia(self):
        self._energia_estado_event.set()

    def _loop_estado_energia(self):
        estado_ativo = False
        while not self._energia_stop_event.is_set():
            self._energia_estado_event.wait(timeout=20 if estado_ativo else 2)
            self._energia_estado_event.clear()

            deve_manter_monitor = self._deve_impedir_suspensao_monitor()
            if deve_manter_monitor:
                resultado = kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                )
                if resultado and not estado_ativo:
                    log("Economia de energia suspensa durante a pausa para manter o monitor ligado.")
                    estado_ativo = True
                elif not resultado and estado_ativo:
                    estado_ativo = False
                    log("Falha ao renovar a prevenção de suspensão do monitor durante a pausa.")
            elif estado_ativo:
                kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                estado_ativo = False
                log("Economia de energia restaurada após a pausa.")

        if estado_ativo:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS)

    def mostrar_tela_pausa(self):
        if not self.config["bloquear_pausa"] or self.tela_pausas or self.pausado or not self.modo_pausa or self._pausa_liberada_emergencia:
            return

        monitores = []
        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            mi = MONITORINFOEX()
            mi.cbSize = ctypes.sizeof(MONITORINFOEX)
            user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
            rect = mi.rcMonitor
            monitores.append({
                "x": rect.left, "y": rect.top,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top
            })
            return True

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
        )
        user32.EnumDisplayMonitors(None, None, callback_type(callback), 0)

        if not monitores:
            monitores = [{"x": 0, "y": 0, "width": 1920, "height": 1080}]

        if TECLADO_GLOBAL:
            keyboard.add_hotkey('ctrl+alt+shift+q', self.desbloquear_emergencia)

        if self.tempo_total_pausa <= 0:
            self.tempo_total_pausa = self.tempo_restante

        WIN_BG = "#0078D7"

        for m in monitores:
            tela = Toplevel(self.janela)
            tela.title("")
            tela.configure(bg=WIN_BG)
            tela.overrideredirect(True)
            tela.attributes("-topmost", True)
            tela.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")

            def bloquear_mouse(e): return "break"
            for ev in ["<Motion>", "<Button-1>", "<Button-2>", "<Button-3>"]:
                tela.bind(ev, bloquear_mouse)

            frame = tk.Frame(tela, bg=WIN_BG)
            frame.place(relx=0.5, rely=0.5, anchor="center")

            canvas_size = 120
            canvas = tk.Canvas(frame, width=canvas_size, height=canvas_size,
                               bg=WIN_BG, highlightthickness=0)
            canvas.pack(pady=(0, 40))

            label_percent = tk.Label(frame, text="Trabalhando nas atualizações 0%",
                                     fg="white", bg=WIN_BG, font=("Segoe UI", 26))
            label_percent.pack(pady=(0, 15))

            label_msg = tk.Label(frame,
                                 text="Não desligue o computador. Isso pode demorar um pouco.",
                                 fg="white", bg=WIN_BG, font=("Segoe UI", 12))
            label_msg.pack(pady=(0, 10))

            label_msg2 = tk.Label(frame,
                                  text="O computador será reiniciado várias vezes.",
                                  fg="white", bg=WIN_BG, font=("Segoe UI", 12))
            label_msg2.pack(pady=(0, 5))

            angle_var = [0]

            def animar_pontos(canvas_ref=canvas, angle_ref=angle_var,
                              tela_ref=tela, cs=canvas_size):
                if not tela_ref.winfo_exists() or not canvas_ref.winfo_exists():
                    return
                try:
                    canvas_ref.delete("dots")
                    cx, cy = cs // 2, cs // 2
                    radius = 35
                    num_dots = 12
                    for i in range(num_dots):
                        a = math.radians(angle_ref[0] + i * (360 / num_dots))
                        x = cx + radius * math.cos(a)
                        y = cy + radius * math.sin(a)
                        brightness = max(40, 255 - i * 20)
                        color = f"#{brightness:02x}{brightness:02x}{brightness:02x}"
                        dot_size = max(2, 5 - i * 0.3)
                        canvas_ref.create_oval(
                            x - dot_size, y - dot_size,
                            x + dot_size, y + dot_size,
                            fill=color, outline="", tags="dots")
                    angle_ref[0] = (angle_ref[0] - 6) % 360
                    tela_ref.after(50, animar_pontos, canvas_ref, angle_ref, tela_ref, cs)
                except Exception:
                    return

            def atualizar_cronometro_tela(tela_ref=tela, label_ref=label_percent):
                if not self.rodando or not tela_ref.winfo_exists() or not label_ref.winfo_exists():
                    return
                if self.tempo_restante > 0 and not self.pausado:
                    total = self.tempo_total_pausa if self.tempo_total_pausa > 0 else 1
                    elapsed = total - self.tempo_restante
                    percent = min(99, int((elapsed / total) * 100))
                    label_ref.config(text=f"Trabalhando nas atualizações {percent}%")
                elif self.tempo_restante <= 0:
                    label_ref.config(text="Trabalhando nas atualizações 100%")
                    tela_ref.after(1500,
                                   lambda: tela_ref.destroy() if tela_ref.winfo_exists() else None)
                    return
                tela_ref.after(1000, atualizar_cronometro_tela, tela_ref, label_ref)

            tela.after(100, animar_pontos, canvas, angle_var, tela, canvas_size)
            tela.after(100, atualizar_cronometro_tela, tela, label_percent)
            self.tela_pausas.append(tela)

    def fechar_tela_pausa(self):
        if TECLADO_GLOBAL:
            try:
                keyboard.remove_hotkey('ctrl+alt+shift+q')
            except:
                pass
        for tela in self.tela_pausas:
            try:
                tela.destroy()
            except:
                pass
        self.tela_pausas.clear()

    def _reset_dia_automatico(self, hoje):
        """Reset automatico ao detectar mudanca de dia (meia-noite)."""
        ontem = self.stats.get("ultimo_dia", hoje)
        trabalho_min = self.tempo_trabalho_hoje // 60
        pausa_min = self.tempo_pausa_hoje // 60
        if trabalho_min > 0 or pausa_min > 0 or self.ciclos_hoje > 0:
            registrar_sessao_diaria(ontem, trabalho_min, pausa_min, self.ciclos_hoje)

        # Parar contagem
        self.modo_pomodoro = False
        self.modo_pausa = False
        self.pausado = False
        self.tempo_restante = 0
        self.fechar_tela_pausa()
        self._iniciar_trabalho_ao_desbloquear = False
        self._sinalizar_atualizacao_energia()

        # Zerar contadores para novo dia
        self.ciclos_hoje = 0
        self.ciclos_concluidos = 0
        self.tempo_trabalho_hoje = 0
        self.tempo_pausa_hoje = 0
        self.tempo_total_pausa = 0
        self.stats = {"ultimo_dia": hoje, "ciclos_hoje": 0}
        salvar_stats(self.stats)

        log(f"Dia {ontem} finalizado automaticamente a meia-noite. Contadores zerados.")
        self.notificar("Novo Dia", f"Dia {ontem} encerrado. Contadores zerados para {hoje}.")
        self.atualizar_interface()

    def iniciar_trabalho(self):
        self._cancelar_aguardo_apos_pausa()
        self._iniciar_trabalho_ao_desbloquear = False
        self._pausado_por_bloqueio = False
        self._pausa_liberada_emergencia = False
        self.modo_pomodoro = True
        self.modo_pausa = False
        self.pausado = False
        self.fechar_tela_pausa()
        self.tempo_restante = self.config["trabalho"] * 60
        self._sinalizar_atualizacao_energia()
        if self.service:
            agora = datetime.now()
            fim = agora + timedelta(minutes=self.config["trabalho"])
            criar_evento_calendar(self.service, "Pomodoro: Foco", agora, fim, f"Sessão de {self.config['trabalho']} min")
        log("Pomodoro iniciado (trabalho).")
        self.notificar("Pomodoro", f"{self.tempo_restante//60} minutos de foco.")
        self.atualizar_tempo()
        self.atualizar_interface()

    def executar_apps_dia(self):
        """Executa os aplicativos configurados no config.ini para o início do dia"""
        apps = self.config.get("apps_inicio_dia", [])
        if not apps:
            return

        log(f"A iniciar {len(apps)} aplicativos de início de dia...")
        for app_path in apps:
            try:
                # Remove aspas se existirem
                path = app_path.strip('"').strip("'")
                if os.path.exists(path) or path.lower() == "cmd.exe" or path.lower() == "explorer.exe":
                    os.startfile(path)
                    log(f"Executado: {path}")
                else:
                    log(f"Ficheiro não encontrado: {path}")
            except Exception as e:
                log(f"Erro ao executar {app_path}: {e}")

    def iniciar_pausa(self):
        self._cancelar_aguardo_apos_pausa()
        self._pausa_liberada_emergencia = False
        self.modo_pomodoro = False
        self.modo_pausa = True
        if self.ciclos_concluidos > 0 and self.ciclos_concluidos % self.config["ciclos_para_pausa_longa"] == 0:
            self.tempo_restante = self.config["pausa_longa"] * 60
            tipo = "longa"
        else:
            self.tempo_restante = self.config["pausa_curta"] * 60
            tipo = "curta"
        self.tempo_total_pausa = self.tempo_restante
        self.tela_bloqueada = False
        self._contagem_desbloqueio = 0
        self._reiniciar_monitoramento_pausa()
        self._sinalizar_atualizacao_energia()
        if self.service:
            agora = datetime.now()
            fim = agora + timedelta(minutes=self.tempo_restante//60)
            criar_evento_calendar(self.service, f"Pausa {tipo.capitalize()}", agora, fim)
        log(f"Pausa {tipo} iniciada.")
        self.notificar("Pausa", f"{self.tempo_restante//60} minutos de descanso.")
        self.pausado = False
        self.mostrar_tela_pausa()
        self.atualizar_tempo()
        self.atualizar_interface()

    def alternar_pausa(self):
        if self.tela_bloqueada:
            self.tela_bloqueada = False
            self._contagem_desbloqueio = 0
            self._iniciar_trabalho_ao_desbloquear = False
        self._pausado_por_bloqueio = False
        self._cancelar_aguardo_apos_pausa()
        self.pausado = not self.pausado
        self.fechar_tela_pausa()
        if not self.pausado and self.modo_pausa:
            self.mostrar_tela_pausa()
        self._sinalizar_atualizacao_energia()
        estado = "Pausado" if self.pausado else "Retomado"
        log(f"Cronômetro {estado}.")
        self.notificar("Pomodoro", f"Cronômetro {estado.lower()}.")
        self.atualizar_tempo()

    def reiniciar(self):
        if self.modo_pomodoro:
            self.tempo_restante = self.config["trabalho"] * 60
        elif self.modo_pausa:
            self.iniciar_pausa()
        log("Cronômetro reiniciado.")
        self.notificar("Pomodoro", "Cronômetro reiniciado.")
        self.atualizar_interface()
        self.atualizar_tempo()

    def encerrar_sessao(self):
        if self.modo_pomodoro:
            self.ciclos_concluidos += 1
            self.ciclos_hoje += 1
            self.stats["ciclos_hoje"] = self.ciclos_hoje
            salvar_stats(self.stats)

            hoje = str(date.today())
            registrar_sessao_diaria(
                data_str=hoje,
                trabalho_min=self.config["trabalho"],
                pausa_min=0,
                ciclos=1
            )

            log(f"Ciclo concluído. Total: {self.ciclos_concluidos} | Hoje: {self.ciclos_hoje}")
            self.notificar("Fim do trabalho!", f"Ciclo {self.ciclos_hoje} do dia concluído! Pausa iniciada.")
            self.iniciar_pausa()
        elif self.modo_pausa:
            log("Pausa finalizada.")
            self.fechar_tela_pausa()
            self._pausa_liberada_emergencia = False
            self.modo_pausa = False
            self.tempo_restante = 0
            self.tempo_total_pausa = 0
            self._sinalizar_atualizacao_energia()
            self.atualizar_interface()
            try:
                winsound.Beep(1000, 600)
            except:
                pass
            if self.tela_bloqueada:
                # Tela ja está bloqueada (utilizador ficou inativo durante a pausa)
                self._iniciar_trabalho_ao_desbloquear = True
                self.pausado = True
                self.notificar("Pausa finalizada!", "Trabalho inicia ao desbloquear.")
                log("Pausa finalizada com tela bloqueada. Trabalho inicia ao desbloquear.")
            else:
                self._aguardar_retorno_apos_pausa()
            self.atualizar_tempo()

    def _reiniciar_monitoramento_pausa(self):
        self._ultimo_movimento_pausa = time.monotonic()
        self._posicao_mouse_pausa = obter_posicao_mouse()
        self._ultima_atividade_pausa = obter_ultima_atividade_usuario()

    def _monitorar_inatividade_pausa(self):
        """Mantém a tela de pausa visível durante o descanso, sem insistir após desbloqueio de emergência."""
        if self._pausa_liberada_emergencia:
            if self.tela_pausas:
                self.fechar_tela_pausa()
            return

        if self.modo_pausa and not self.pausado and self.config.get("bloquear_pausa"):
            if not self.tela_pausas:
                self.mostrar_tela_pausa()
        elif self.tela_pausas and (not self.modo_pausa or self.pausado):
            self.fechar_tela_pausa()

    def _cancelar_aguardo_apos_pausa(self):
        self._aguardando_retorno_apos_pausa = False
        self._deadline_retorno_apos_pausa = None
        self._posicao_mouse_apos_pausa = None
        self._ultima_atividade_apos_pausa = None
        self._ultimo_movimento_pausa = None
        self._posicao_mouse_pausa = None
        self._ultima_atividade_pausa = None

    def _aguardar_retorno_apos_pausa(self):
        """Aguarda até 5 segundos por atividade antes de bloquear a tela."""
        self._aguardando_retorno_apos_pausa = True
        self._deadline_retorno_apos_pausa = time.monotonic() + 5
        self._posicao_mouse_apos_pausa = obter_posicao_mouse()
        self._ultima_atividade_apos_pausa = obter_ultima_atividade_usuario()
        log("Pausa finalizada. Aguardando atividade por 5 segundos.")
        self.notificar("Pausa finalizada!", "Mexa no rato ou teclado em até 5 segundos para iniciar o trabalho automaticamente.")
        self.atualizar_tempo()

    def _bloquear_apos_pausa(self):
        """Bloqueia a tela após a pausa se não houver atividade do utilizador."""
        if self.modo_pomodoro:
            self._cancelar_aguardo_apos_pausa()
            return
        self._cancelar_aguardo_apos_pausa()
        bloquear_tela()
        self._iniciar_trabalho_ao_desbloquear = True
        self.tela_bloqueada = True
        self.pausado = True
        self._contagem_desbloqueio = 0
        self._sinalizar_atualizacao_energia()
        log("Sem atividade após a pausa. Tela bloqueada.")

    def comecar_dia(self):
        self._cancelar_aguardo_apos_pausa()
        hoje = str(date.today())
        if self.stats["ultimo_dia"] == hoje and self.ciclos_hoje > 0:
            if not messagebox.askyesno("Começar o Dia", "Isso vai zerar os ciclos de hoje. Continuar?"):
                return

        # Parar toda contagem ativa
        self.modo_pomodoro = False
        self.modo_pausa = False
        self.pausado = False
        self.tempo_restante = 0
        self.fechar_tela_pausa()
        self._iniciar_trabalho_ao_desbloquear = False
        self._sinalizar_atualizacao_energia()
        if self.job_id:
            self.janela.after_cancel(self.job_id)
            self.job_id = None

        self.ciclos_hoje = 0
        self.ciclos_concluidos = 0
        self.tempo_trabalho_hoje = 0
        self.tempo_pausa_hoje = 0
        self.tempo_total_pausa = 0
        self.stats = {"ultimo_dia": hoje, "ciclos_hoje": 0}
        salvar_stats(self.stats)

        log("Novo dia iniciado! Contador zerado.")
        self.notificar("Novo Dia", "Jornada reiniciada com sucesso!")
        
        # Executar aplicativos de início de dia
        self.executar_apps_dia()
        
        self.atualizar_interface()

    def hora_almoco(self):
        self._cancelar_aguardo_apos_pausa()
        if not messagebox.askyesno("Hora do Almoço", "Bloquear tela para almoço? Trabalho inicia ao desbloquear."):
            return
        # Parar qualquer contagem ativa
        self.modo_pomodoro = False
        self.modo_pausa = False
        self.pausado = True
        self.tempo_restante = 0
        self.tempo_total_pausa = 0
        self.fechar_tela_pausa()
        self._sinalizar_atualizacao_energia()
        self.atualizar_interface()
        # Registrar evento no Calendar se disponivel
        if self.service:
            agora = datetime.now()
            fim = agora + timedelta(minutes=60)
            criar_evento_calendar(self.service, "Almoço", agora, fim, "Pausa para refeição")
        log("Hora do almoço. Tela bloqueada. Trabalho inicia ao desbloquear.")
        self.notificar("Hora do Almoço", "Tela será bloqueada. Trabalho inicia ao desbloquear.")
        # Bloquear tela e preparar auto-start
        bloquear_tela()
        self._iniciar_trabalho_ao_desbloquear = True
        self.tela_bloqueada = True
        self._contagem_desbloqueio = 0

    def finalizar_dia(self):
        self._cancelar_aguardo_apos_pausa()
        if not messagebox.askyesno("Finalizar o Dia", "Salvar stats, criar resumo no Calendar e zerar?"):
            return
        hoje = str(date.today())
        trabalho_min = self.tempo_trabalho_hoje // 60
        pausa_min = self.tempo_pausa_hoje // 60
        registrar_sessao_diaria(hoje, trabalho_min, pausa_min, self.ciclos_hoje)
        if self.service:
            agora = datetime.now()
            fim = agora + timedelta(hours=1)
            descricao = f"Resumo: {self.ciclos_hoje} ciclos | {trabalho_min} min trabalhados | {pausa_min} min pausas"
            criar_evento_calendar(self.service, "Resumo do Dia - Pomodoro", agora, fim, descricao)
        # Parar toda contagem ativa
        self.modo_pomodoro = False
        self.modo_pausa = False
        self.pausado = False
        self.tempo_restante = 0
        self.fechar_tela_pausa()
        self._iniciar_trabalho_ao_desbloquear = False
        self._sinalizar_atualizacao_energia()
        if self.job_id:
            self.janela.after_cancel(self.job_id)
            self.job_id = None
        self.comecar_dia()  # Zera contadores
        self.notificar("Fim do Dia", "Jornada finalizada e salva!")
        log("Dia finalizado.")

    def mostrar_estatisticas(self):
        stats = obter_estatisticas()
        janela_stats = Toplevel(self.janela)
        janela_stats.title("Estatísticas - Pomodoro")
        janela_stats.geometry("650x450")
        janela_stats.configure(bg="#1C1C28")

        tree = ttk.Treeview(janela_stats, columns=("Data", "Trabalho", "Pausa", "Ciclos"), show="headings")
        tree.heading("Data", text="Data")
        tree.heading("Trabalho", text="Trabalho (min)")
        tree.heading("Pausa", text="Pausa (min)")
        tree.heading("Ciclos", text="Ciclos")
        tree.column("Data", width=120, anchor="center")
        tree.column("Trabalho", width=140, anchor="center")
        tree.column("Pausa", width=120, anchor="center")
        tree.column("Ciclos", width=100, anchor="center")

        for row in stats:
            tree.insert("", "end", values=row)

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        total_trab = sum(r[1] for r in stats)
        total_pausa = sum(r[2] for r in stats)
        total_ciclos = sum(r[3] for r in stats)
        tk.Label(janela_stats, text=f"Totais → Trabalho: {total_trab} min | Pausa: {total_pausa} min | Ciclos: {total_ciclos}",
                 fg="#00FFFF", bg="#1C1C28", font=("Orbitron", 10)).pack(pady=5)

    def mostrar_graficos(self):
        stats = obter_estatisticas()
        if not stats:
            messagebox.showinfo("Gráficos", "Nenhum dado para exibir.")
            return

        janela_graf = Toplevel(self.janela)
        janela_graf.title("Gráficos - Pomodoro Analytics")
        janela_graf.geometry("900x600")
        janela_graf.configure(bg="#1C1C28")

        notebook = ttk.Notebook(janela_graf)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # === ABA 1: Ciclos por Dia ===
        frame1 = ttk.Frame(notebook)
        notebook.add(frame1, text="Ciclos por Dia")

        fig1 = Figure(figsize=(8, 5), dpi=100, facecolor="#1C1C28")
        ax1 = fig1.add_subplot(111)
        datas = [row[0] for row in stats[:14]]  # últimos 14 dias
        ciclos = [row[3] for row in stats[:14]]
        ax1.bar(datas, ciclos, color="#00FFFF")
        ax1.set_title("Ciclos Concluídos por Dia", color="white")
        ax1.set_xlabel("Data", color="white")
        ax1.set_ylabel("Ciclos", color="white")
        ax1.tick_params(colors="white")
        ax1.grid(True, alpha=0.3)
        fig1.patch.set_facecolor("#1C1C28")
        ax1.set_facecolor("#2D2D3A")

        canvas1 = FigureCanvasTkAgg(fig1, frame1)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True)

        # === ABA 2: Trabalho vs Pausa ===
        frame2 = ttk.Frame(notebook)
        notebook.add(frame2, text="Trabalho vs Pausa")

        fig2 = Figure(figsize=(8, 5), dpi=100, facecolor="#1C1C28")
        ax2 = fig2.add_subplot(111)
        total_trab = sum(r[1] for r in stats)
        total_pausa = sum(r[2] for r in stats)
        labels = ['Trabalho', 'Pausa']
        sizes = [total_trab, total_pausa]
        colors = ['#00FF7F', '#FFD700']
        if sum(sizes) > 0:
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.set_title("Distribuição de Tempo", color="white")
        else:
            ax2.text(0.5, 0.5, "Sem dados de tempo registados", ha='center', va='center',
                     fontsize=14, color='white', transform=ax2.transAxes)
            ax2.set_title("Distribuição de Tempo", color="white")
        fig2.patch.set_facecolor("#1C1C28")

        canvas2 = FigureCanvasTkAgg(fig2, frame2)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True)

        # === ABA 3: Progresso Semanal ===
        frame3 = ttk.Frame(notebook)
        notebook.add(frame3, text="Progresso Semanal")

        fig3 = Figure(figsize=(8, 5), dpi=100, facecolor="#1C1C28")
        ax3 = fig3.add_subplot(111)
        datas_full = [datetime.strptime(row[0], "%Y-%m-%d") for row in stats]
        ciclos_full = [row[3] for row in stats]
        if datas_full:
            ax3.plot(datas_full, ciclos_full, marker='o', color="#FF69B4", linewidth=2)
            ax3.set_title("Evolução dos Ciclos", color="white")
            ax3.set_xlabel("Data", color="white")
            ax3.set_ylabel("Ciclos Acumulativos", color="white")
            ax3.tick_params(colors="white")
            ax3.grid(True, alpha=0.3)
        fig3.patch.set_facecolor("#1C1C28")
        ax3.set_facecolor("#2D2D3A")

        canvas3 = FigureCanvasTkAgg(fig3, frame3)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill="both", expand=True)

    def obter_texto_tray(self, modo, texto):
        return f"Pomodoro Premium | {modo} | Restante: {texto}"

    def criar_icone_progresso(self, progresso):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, size, size), fill=(30, 30, 30, 255))
        if progresso > 0:
            draw.pieslice((4, 4, size-4, size-4), start=-90, end=-90 + 360 * progresso, fill=(0, 255, 255))
        draw.ellipse((16, 16, size-16, size-16), fill=(30, 30, 30, 255))
        texto = f"{self.ciclos_hoje}" if self.ciclos_hoje > 0 else "00"
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), texto, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((size - w) / 2, (size - h) / 2), texto, font=font, fill=(0, 255, 255))
        return img

    def criar_menu(self):
        return (
            item("Mostrar Janela", self.mostrar_janela),
            item("Iniciar Trabalho", lambda icon, item: self.iniciar_trabalho()),
            item("Iniciar Pausa", lambda icon, item: self.iniciar_pausa()),
            item("Pausar / Retomar", lambda icon, item: self.alternar_pausa()),
            item("Reiniciar", lambda icon, item: self.reiniciar()),
            item("Começar o Dia", lambda icon, item: self.comecar_dia()),
            item("Hora do Almoço", lambda icon, item: self.hora_almoco()),
            item("Finalizar o Dia", lambda icon, item: self.finalizar_dia()),
            item("Estatísticas", lambda icon, item: self.mostrar_estatisticas()),
            item("Gráficos", lambda icon, item: self.mostrar_graficos()),
            item("Bloquear Tela (Win+L)", lambda icon, item: self.bloquear_e_pausar()),
            item("Sair", lambda icon, item: self.sair())
        )

    def mostrar_janela(self):
        if self.janela:
            self.janela.deiconify()
            self.janela.lift()
            self.janela.attributes("-topmost", True)

    def sair(self):
        self._cancelar_aguardo_apos_pausa()
        hoje = str(date.today())
        registrar_sessao_diaria(
            data_str=hoje,
            trabalho_min=self.tempo_trabalho_hoje // 60,
            pausa_min=self.tempo_pausa_hoje // 60,
            ciclos=0
        )

        self.rodando = False
        self.fechar_tela_pausa()
        self._sinalizar_atualizacao_energia()
        self._energia_stop_event.set()
        self._thread_energia.join(timeout=1)
        # Remover hotkey global Win+L
        if TECLADO_GLOBAL:
            try:
                keyboard.remove_hotkey('win+l')
            except:
                pass
        if self.job_id:
            try:
                self.janela.after_cancel(self.job_id)
            except:
                pass
        if self.janela:
            self.janela.quit()
        if self.icone:
            self.icone.stop()
        log("Aplicação encerrada.")

    def run(self):
        criar_config_padrao()
        self.config = carregar_config()

        self.icone = pystray.Icon("PomodoroTray", self.criar_icone_progresso(0), self.obter_texto_tray("PARADO", "00:00"), self.criar_menu())
        threading.Thread(target=self.icone.run, daemon=True).start()

        if self.config["mostrar_janela"]:
            self.criar_janela()
            self.janela.after(100, self.atualizar_interface)
            self.janela.mainloop()
        else:
            while self.rodando:
                time.sleep(0.1)


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
