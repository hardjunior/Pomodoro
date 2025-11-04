import time
import threading
import os
import logging
import configparser
import json
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

# ==============================
# FORÇA DPI UNAWARE (PIXELS FÍSICOS)
# ==============================
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# ==============================
# WINDOWS API
# ==============================
user32 = ctypes.windll.user32

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

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(message)s")
def log(msg):
    print(msg)
    logging.info(msg)

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
        with open(CONFIG_FILE, "w") as f:
            config.write(f)

def carregar_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    pomodoro = config["Pomodoro"]
    janela = config["Janela"] if "Janela" in config else {"mostrar_janela": "True"}
    icone = config["Icone"] if "Icone" in config else {"arquivo": "pomodoro.ico"}
    return {
        "trabalho": int(pomodoro["tempo_trabalho"]),
        "pausa_curta": int(pomodoro["pausa_curta"]),
        "pausa_longa": int(pomodoro["pausa_longa"]),
        "ciclos_para_pausa_longa": int(pomodoro["ciclos_para_pausa_longa"]),
        "bloquear_pausa": pomodoro.get("bloquear_pausa", "True") == "True",
        "mostrar_janela": janela.get("mostrar_janela", "True") == "True",
        "arquivo_icone": icone.get("arquivo", "pomodoro.ico")
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

        init_db()

    def notificar(self, titulo, mensagem):
        notification.notify(title=titulo, message=mensagem, timeout=5, app_name="Pomodoro Tray")
        try:
            winsound.Beep(880, 400)
        except:
            pass

    def criar_janela(self):
        self.janela = tk.Tk()
        self.janela.title("Pomodoro Premium")
        self.janela.geometry("300x460")
        self.janela.resizable(False, False)
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

        style = {"width": 20, "padx": 5, "pady": 3, "font": ("Orbitron", 11, "bold")}
        tk.Button(frame_botoes, text="Iniciar Trabalho", command=self.iniciar_trabalho, bg="#00FF7F", fg="black", **style).grid(row=0, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Iniciar Pausa", command=self.iniciar_pausa, bg="#FFD700", fg="black", **style).grid(row=1, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Pausar / Retomar", command=self.alternar_pausa, bg="#FF69B4", fg="white", **style).grid(row=2, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Reiniciar", command=self.reiniciar, bg="#FF4500", fg="white", **style).grid(row=3, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Começar o Dia", command=self.comecar_dia, bg="#9400D3", fg="white", **style).grid(row=4, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Estatísticas", command=self.mostrar_estatisticas, bg="#1E90FF", fg="white", **style).grid(row=5, column=0, padx=5, pady=3)
        tk.Button(frame_botoes, text="Gráficos", command=self.mostrar_graficos, bg="#FF1493", fg="white", **style).grid(row=6, column=0, padx=5, pady=3)

        self.janela.protocol("WM_DELETE_WINDOW", self.janela.withdraw)
        self.janela.bind("<Control-l>", lambda e: bloquear_tela())
        return self.janela

    def atualizar_tempo(self):
        if self.job_id:
            self.janela.after_cancel(self.job_id)
        self.job_id = self.janela.after(1000, self.tick)

    def tick(self):
        if self.rodando and self.tempo_restante > 0 and not self.pausado:
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
        if self.icone:
            self.icone.icon = self.criar_icone_progresso(self.calcular_progresso())
        modo = "TRABALHO" if self.modo_pomodoro else "PAUSA"
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
        log("TECLA SECRETA ATIVADA: Pausa desbloqueada!")
        self.fechar_tela_pausa()
        self.pausado = False
        self.atualizar_tempo()
        self.notificar("EMERGÊNCIA", "Pausa desbloqueada!")

    def mostrar_tela_pausa(self):
        if not self.config["bloquear_pausa"] or self.tela_pausas:
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

        for m in monitores:
            tela = Toplevel(self.janela)
            tela.title("PAUSA OBRIGATÓRIA")
            tela.configure(bg="black")
            tela.overrideredirect(True)
            tela.attributes("-topmost", True)
            tela.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")

            def bloquear_mouse(e): return "break"
            for ev in ["<Motion>", "<Button-1>", "<Button-2>", "<Button-3>"]:
                tela.bind(ev, bloquear_mouse)

            frame = tk.Frame(tela, bg="black")
            frame.pack(expand=True)

            tk.Label(frame, text="PAUSA — NÃO MEXA!", fg="#00FFFF", bg="black", font=("Orbitron", 48, "bold")).pack(pady=20)
            label_cronometro = tk.Label(frame, text="00:00", fg="#FF4500", bg="black", font=("Orbitron", 72, "bold"))
            label_cronometro.pack(pady=30)

            def atualizar_cronometro_tela(tela_ref=tela, label_ref=label_cronometro):
                if not self.rodando or not tela_ref.winfo_exists():
                    return
                if self.tempo_restante > 0 and not self.pausado:
                    mins, secs = divmod(self.tempo_restante, 60)
                    label_ref.config(text=f"{mins:02d}:{secs:02d}")
                elif self.tempo_restante <= 0:
                    try:
                        tela_ref.destroy()
                    except:
                        pass
                    return
                tela_ref.after(1000, atualizar_cronometro_tela, tela_ref, label_ref)

            tela.after(100, atualizar_cronometro_tela, tela, label_cronometro)
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

    def iniciar_trabalho(self):
        self.modo_pomodoro = True
        self.modo_pausa = False
        self.fechar_tela_pausa()
        if self.tempo_restante <= 0:
            self.tempo_restante = self.config["trabalho"] * 60
        log("Pomodoro iniciado (trabalho).")
        self.notificar("Pomodoro", f"{self.tempo_restante//60} minutos de foco.")
        self.atualizar_tempo()
        self.atualizar_interface()

    def iniciar_pausa(self):
        self.modo_pomodoro = False
        self.modo_pausa = True
        if self.ciclos_concluidos > 0 and self.ciclos_concluidos % self.config["ciclos_para_pausa_longa"] == 0:
            self.tempo_restante = self.config["pausa_longa"] * 60
            tipo = "longa"
        else:
            self.tempo_restante = self.config["pausa_curta"] * 60
            tipo = "curta"
        log(f"Pausa {tipo} iniciada.")
        self.notificar("Pausa", f"{self.tempo_restante//60} minutos de descanso.")
        self.mostrar_tela_pausa()
        self.atualizar_tempo()
        self.atualizar_interface()

    def alternar_pausa(self):
        self.pausado = not self.pausado
        if self.pausado:
            self.mostrar_tela_pausa()
        else:
            self.fechar_tela_pausa()
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
            self.notificar("Fim do trabalho!", f"Ciclo {self.ciclos_hoje} do dia concluído!")
            self.iniciar_pausa()
        elif self.modo_pausa:
            log("Pausa finalizada.")
            try:
                winsound.Beep(1000, 600)
            except:
                pass
            self.iniciar_trabalho()

    def comecar_dia(self):
        hoje = str(date.today())
        if self.stats["ultimo_dia"] == hoje and self.ciclos_hoje > 0:
            if not messagebox.askyesno("Começar o Dia", "Isso vai zerar os ciclos de hoje. Continuar?"):
                return

        self.ciclos_hoje = 0
        self.tempo_trabalho_hoje = 0
        self.tempo_pausa_hoje = 0
        self.stats = {"ultimo_dia": hoje, "ciclos_hoje": 0}
        salvar_stats(self.stats)

        log("Novo dia iniciado! Contador zerado.")
        self.notificar("Novo Dia", "Jornada reiniciada com sucesso!")
        self.atualizar_interface()

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
        ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
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
            item("Estatísticas", lambda icon, item: self.mostrar_estatisticas()),
            item("Gráficos", lambda icon, item: self.mostrar_graficos()),
            item("Bloquear Tela (Ctrl+L)", lambda icon, item: bloquear_tela()),
            item("Sair", lambda icon, item: self.sair())
        )

    def mostrar_janela(self):
        if self.janela:
            self.janela.deiconify()
            self.janela.lift()
            self.janela.attributes("-topmost", True)

    def sair(self):
        hoje = str(date.today())
        registrar_sessao_diaria(
            data_str=hoje,
            trabalho_min=self.tempo_trabalho_hoje // 60,
            pausa_min=self.tempo_pausa_hoje // 60,
            ciclos=0
        )

        self.rodando = False
        self.fechar_tela_pausa()
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

        self.icone = pystray.Icon("PomodoroTray", self.criar_icone_progresso(0), "Pomodoro Premium", self.criar_menu())
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