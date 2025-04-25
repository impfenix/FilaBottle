import tkinter as tk
from tkinter import ttk, messagebox
import serial
import threading
import platform
from serial.tools import list_ports
import ctypes
import sys
import os

# Configurações iniciais
temperatura = 0.0
porta_serial = None
arduino = None
leitura_ativa = True

# Valores de controle
velocidade_motor = 40  # mm/s
temp_min_motor = 180.0
temperatura_minima = 245.0
temperatura_maxima = 260.0

# Função para encontrar portas seriais
def listar_portas():
    return [port.device for port in list_ports.comports()]

# Conectar com a porta selecionada
def conectar():
    global arduino, porta_serial
    porta_serial = porta_var.get()
    if arduino and arduino.is_open:
        arduino.close()
    try:
        arduino = serial.Serial(porta_serial, 9600, timeout=1)
    except Exception as e:
        print("Erro ao conectar:", e)

# Enviar configurações para o Arduino
def aplicar_configuracoes():
    global velocidade_motor, temperatura_maxima, temp_min_motor
    try:
        if arduino and arduino.is_open:
            comando = f"SET,{velocidade_motor},{temperatura_maxima},{temp_min_motor}\n"
            arduino.write(comando.encode())
            status_label.config(text="✔ Configurações aplicadas com sucesso!", fg="green")
        else:
            status_label.config(text="❌ Porta serial não conectada!", fg="red")
    except ValueError:
        messagebox.showerror("Erro", "Certifique-se de que todos os campos estão preenchidos corretamente.")
        status_label.config(text="❌ Erro ao aplicar configurações.", fg="red")

    root.after(5000, lambda: status_label.config(text=""))

# Atualizar exibição da temperatura e status do motor
def atualizar_display():
    try:
        if arduino and arduino.in_waiting:
            linha = arduino.readline().decode().strip()
            if linha.startswith("Temperatura:"):
                valor = float(linha.split(":")[1].strip().replace(" °C", ""))
                cor = "#00FF00"  # verde
                if valor > 36:
                    intensidade = min(int((valor - 36) * 4), 255)
                    cor = f"#{intensidade:02x}{(255-intensidade):02x}00"
                temperatura_var.set(f"{valor:.2f} °C")
                display.config(fg=cor)

                if valor >= temp_min_motor:
                    motor_status_var.set(f"{velocidade_motor:.2f} mm/s")
                else:
                    motor_status_var.set("OFF")
    except Exception as e:
        print("Erro na leitura:", e)
    root.after(500, atualizar_display)

# Função de ajuste de valores com suporte a pressionar e segurar
class BotaoPressionado:
    def __init__(self, button, tipo, delta):
        self.button = button
        self.tipo = tipo
        self.delta = delta
        self.running = False
        self.button.bind('<ButtonPress-1>', self.start)
        self.button.bind('<ButtonRelease-1>', self.stop)

    def start(self, event):
        self.running = True
        self.repeat()

    def stop(self, event):
        self.running = False

    def repeat(self):
        if self.running:
            alterar_valor(self.tipo, self.delta)
            root.after(100, self.repeat)

# Construção da interface
root = tk.Tk()
root.title("Fila Pet Controller Alpha 0.1")
root.geometry("320x500")

# Configurar ícone da janela
icon_path = r"C:\\Users\\luana\\Downloads\\Fila Pet Controller\\FilaPetController.ico"
if os.path.exists(icon_path):
    root.iconbitmap(icon_path)

# Detectar e aplicar tema do sistema (escuro ou claro) no Windows
def is_dark_mode_windows():
    try:
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
        key = winreg.OpenKey(registry, key_path)
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0  # 0 = modo escuro, 1 = modo claro
    except Exception:
        return False  # padrão: claro

modo_escuro = is_dark_mode_windows()

# Aplicar cores com base no tema
tema_sistema = "clam"
if platform.system() == "Windows":
    tema_sistema = "vista"

style = ttk.Style()
style.theme_use(tema_sistema)

bg_color = "#1e1e1e" if modo_escuro else "SystemButtonFace"
fg_color = "white" if modo_escuro else "black"

root.configure(bg=bg_color)

# Tentar alterar a barra de título para escura (Windows 10+)
if modo_escuro and sys.platform == "win32":
    try:
        HWND = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1)))
    except Exception:
        pass

# Porta Serial
porta_var = tk.StringVar(value="Selecione a porta")
porta_menu = ttk.Combobox(root, textvariable=porta_var, values=listar_portas(), state="readonly")
porta_menu.pack(pady=10)
conectar_btn = ttk.Button(root, text="Conectar", command=conectar)
conectar_btn.pack(pady=5)

# Display de temperatura
temperatura_var = tk.StringVar(value="--.-- °C")
display = tk.Label(root, textvariable=temperatura_var, font=("Courier", 32, "bold"), bg="black", fg="green", width=12)
display.pack(pady=20)

# Display status do motor
motor_status_var = tk.StringVar(value="OFF")
motor_status_label = tk.Label(root, textvariable=motor_status_var, font=("Courier", 20, "bold"), bg="black", fg="blue", width=12)
motor_status_label.pack(pady=(0, 20))

# Controles de velocidade
frame_vel = tk.LabelFrame(root, text="Velocidade", bg=bg_color, fg=fg_color)
frame_vel.pack(pady=5)
vel_btn_menos = tk.Button(frame_vel, text="-", width=4)
vel_btn_menos.pack(side=tk.LEFT, padx=5)
vel_label = tk.Label(frame_vel, text=f"{velocidade_motor}", width=5, bg=bg_color, fg=fg_color)
vel_label.pack(side=tk.LEFT)
vel_btn_mais = tk.Button(frame_vel, text="+", width=4)
vel_btn_mais.pack(side=tk.LEFT, padx=5)

# Controles de temperatura de acionamento do motor
frame_motor = tk.LabelFrame(root, text="Motor Ativa em C°", bg=bg_color, fg=fg_color)
frame_motor.pack(pady=5)
motor_btn_menos = tk.Button(frame_motor, text="-", width=4)
motor_btn_menos.pack(side=tk.LEFT, padx=5)
min_label = tk.Label(frame_motor, text=f"{temp_min_motor:.0f}", width=5, bg=bg_color, fg=fg_color)
min_label.pack(side=tk.LEFT)
motor_btn_mais = tk.Button(frame_motor, text="+", width=4)
motor_btn_mais.pack(side=tk.LEFT, padx=5)

# Controles de temperatura mínima
frame_temp_min = tk.LabelFrame(root, text="Temperatura Mínima C°", bg=bg_color, fg=fg_color)
frame_temp_min.pack(pady=5)
temp_min_btn_menos = tk.Button(frame_temp_min, text="-", width=4)
temp_min_btn_menos.pack(side=tk.LEFT, padx=5)
temp_minima_label = tk.Label(frame_temp_min, text=f"{temperatura_minima:.0f}", width=5, bg=bg_color, fg=fg_color)
temp_minima_label.pack(side=tk.LEFT)
temp_min_btn_mais = tk.Button(frame_temp_min, text="+", width=4)
temp_min_btn_mais.pack(side=tk.LEFT, padx=5)

# Controles de temperatura máxima
frame_temp_max = tk.LabelFrame(root, text="Temperatura Máxima C°", bg=bg_color, fg=fg_color)
frame_temp_max.pack(pady=5)
temp_max_btn_menos = tk.Button(frame_temp_max, text="-", width=4)
temp_max_btn_menos.pack(side=tk.LEFT, padx=5)
temp_maxima_label = tk.Label(frame_temp_max, text=f"{temperatura_maxima:.0f}", width=5, bg=bg_color, fg=fg_color)
temp_maxima_label.pack(side=tk.LEFT)
temp_max_btn_mais = tk.Button(frame_temp_max, text="+", width=4)
temp_max_btn_mais.pack(side=tk.LEFT, padx=5)

# Botão aplicar
aplicar_btn = ttk.Button(root, text="Aplicar", command=aplicar_configuracoes)
aplicar_btn.pack(pady=10)

# Status de aplicação
status_label = tk.Label(root, text="", fg="green", font=("Arial", 10))
status_label.pack(pady=(10, 0))

# Função de ajuste de valores
def alterar_valor(tipo, delta):
    global velocidade_motor, temp_min_motor, temperatura_minima, temperatura_maxima
    if tipo == "vel":
        velocidade_motor = max(0, min(velocidade_motor + delta, 100))
        vel_label.config(text=f"{velocidade_motor}")
    elif tipo == "min":
        temp_min_motor = max(0, min(temp_min_motor + delta, 250))
        min_label.config(text=f"{temp_min_motor:.0f}")
    elif tipo == "temp_minima":
        temperatura_minima = max(0, min(temperatura_minima + delta, 250))
        temp_minima_label.config(text=f"{temperatura_minima:.0f}")
    elif tipo == "temp_maxima":
        temperatura_maxima = max(0, min(temperatura_maxima + delta, 300))
        temp_maxima_label.config(text=f"{temperatura_maxima:.0f}")

# Aplicando comportamento pressionar e segurar
BotaoPressionado(vel_btn_menos, "vel", -1)
BotaoPressionado(vel_btn_mais, "vel", 1)
BotaoPressionado(motor_btn_menos, "min", -1)
BotaoPressionado(motor_btn_mais, "min", 1)
BotaoPressionado(temp_min_btn_menos, "temp_minima", -1)
BotaoPressionado(temp_min_btn_mais, "temp_minima", 1)
BotaoPressionado(temp_max_btn_menos, "temp_maxima", -1)
BotaoPressionado(temp_max_btn_mais, "temp_maxima", 1)

# Iniciar leitura
atualizar_display()
root.mainloop()
