import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.utils import platform

import serial
# Importa a exceção específica para tratar desconexões
from serial.serialutil import SerialException

# A listagem de portas padrão só funciona no Desktop
if platform != 'android':
    import serial.tools.list_ports

# A classe ParameterControl não mudou
class ParameterControl(BoxLayout):
    param_name = StringProperty('')
    param_value = NumericProperty(0)
    param_unit = StringProperty('')
    
    def __init__(self, name, value, unit, callback, step=1, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.spacing = 10
        self.param_name = name
        self.param_value = value
        self.param_unit = unit
        self.callback = callback
        self.step = step
        self._update_event = None

        self.add_widget(Label(text=f'{self.param_name}:', size_hint_x=0.4))
        
        btn_minus = Button(text='-', size_hint_x=0.15)
        btn_minus.bind(on_press=self.start_update, on_release=self.stop_update)
        self.add_widget(btn_minus)

        self.value_label = Label(text=self.get_formatted_value(), size_hint_x=0.3)
        self.add_widget(self.value_label)

        btn_plus = Button(text='+', size_hint_x=0.15)
        btn_plus.bind(on_press=self.start_update, on_release=self.stop_update)
        self.add_widget(btn_plus)

    def get_formatted_value(self):
        return f'{self.param_value:.1f} {self.param_unit}'

    def update_value_label(self):
        self.value_label.text = self.get_formatted_value()

    def start_update(self, instance):
        self.stop_update(instance)
        self.update_param(instance.text)
        self._update_event = Clock.schedule_interval(lambda dt: self.update_param(instance.text), 0.1)

    def stop_update(self, instance):
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

    def update_param(self, operation):
        if operation == '+':
            self.param_value += self.step
        else:
            self.param_value -= self.step
        
        if self.param_value < 0:
            self.param_value = 0
            
        self.update_value_label()
        self.callback(self.param_name, self.param_value)


class FilaBottleApp(App):
    COLOR_ON = ListProperty([0.2, 0.8, 0.2, 1])
    COLOR_OFF = ListProperty([0.8, 0.2, 0.2, 1])
    COLOR_NEUTRAL = ListProperty([0.2, 0.2, 0.2, 1])

    def build(self):
        self.arduino = None
        self.system_is_on = False
        self.heater_is_on = False
        self.motor_is_on = False

        self.main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # --- Conexão Serial com Botão Atualizar (SUA NOVA VERSÃO) ---
        connection_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.port_spinner = Spinner(text='Selecione a Porta', values=self.listar_portas(), size_hint_x=0.6)
        
        self.refresh_btn = Button(text='Atualizar', on_press=self.refresh_ports, size_hint_x=0.2)
        
        self.connect_btn = Button(text='Conectar', on_press=self.conectar, size_hint_x=0.2)
        connection_layout.add_widget(self.port_spinner)
        connection_layout.add_widget(self.refresh_btn)
        connection_layout.add_widget(self.connect_btn)
        self.main_layout.add_widget(connection_layout)

        # --- O resto do layout continua igual ---
        self.temp_display = Label(text='--.-- °C', font_size='48sp', size_hint_y=0.3)
        self.main_layout.add_widget(self.temp_display)
        self.status_label = Label(text='Desconectado', size_hint_y=0.1)
        self.main_layout.add_widget(self.status_label)
        self.vel_control = ParameterControl('Velocidade', 40.0, 'mm/s', self.send_param_update, step=0.5)
        self.temp_control = ParameterControl('Temp. Alvo', 120.0, '°C', self.send_param_update, step=1)
        self.motor_temp_control = ParameterControl('Temp. Motor', 90.0, '°C', self.send_param_update, step=1)
        self.main_layout.add_widget(self.vel_control)
        self.main_layout.add_widget(self.temp_control)
        self.main_layout.add_widget(self.motor_temp_control)
        self.master_btn = Button(text='Ligar Sistema', on_press=self.toggle_system, background_color=self.COLOR_NEUTRAL, size_hint_y=0.2)
        self.main_layout.add_widget(self.master_btn)
        individual_controls_layout = GridLayout(cols=2, spacing=10, size_hint_y=0.2)
        self.heater_btn = Button(text='Ligar Aquecedor', on_press=self.toggle_heater, background_color=self.COLOR_OFF)
        self.motor_btn = Button(text='Ligar Motor', on_press=self.toggle_motor, background_color=self.COLOR_OFF)
        individual_controls_layout.add_widget(self.heater_btn)
        individual_controls_layout.add_widget(self.motor_btn)
        self.main_layout.add_widget(individual_controls_layout)

        Clock.schedule_interval(self.read_from_arduino, 0.1)
        return self.main_layout
    
    def on_start(self):
        """ Pede permissões necessárias no Android ao iniciar o app. """
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.USB_HOST])
            except ImportError:
                self.status_label.text = "Erro ao importar permissões."

    # SUA NOVA FUNÇÃO
    def refresh_ports(self, instance):
        """Atualiza a lista de portas seriais disponíveis no spinner."""
        self.port_spinner.values = self.listar_portas()
        self.port_spinner.text = 'Selecione a Porta'

    def listar_portas(self):
        """ Lista as portas seriais disponíveis. Usa um método diferente para Android. """
        if platform == 'android':
            try:
                from usb4a import usb
                devices = usb.get_usb_device_list()
                portas = [d.getDeviceName() for d in devices]
                return portas if portas else ['Nenhuma Porta USB']
            except Exception as e:
                return [f'Erro USB: {str(e)[:20]}']
        else:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            return ports if ports else ['Nenhuma Porta']

    def conectar(self, instance):
        if self.connect_btn.text == 'Conectar':
            port = self.port_spinner.text
            if port not in ['Nenhuma Porta', 'Selecione a Porta', 'Nenhuma Porta USB'] and not port.startswith('Erro USB'):
                try:
                    self.arduino = serial.Serial(port, 9600, timeout=1)
                    self.status_label.text = f"Conectado a {port}"
                    self.connect_btn.text = 'Desconectar'
                except Exception as e:
                    self.status_label.text = f"Erro ao conectar: {e}"
        else:
            if self.arduino: self.arduino.close()
            # SUA NOVA LÓGICA CENTRALIZADA
            self.handle_disconnection()

    # SUA NOVA FUNÇÃO
    def handle_disconnection(self):
        """Função chamada quando a comunicação serial falha."""
        if self.arduino:
            self.arduino.close()
            self.arduino = None
        self.status_label.text = "Arduino Desconectado!"
        self.connect_btn.text = 'Conectar'
        # Reseta a UI para o estado desligado
        self.update_ui(-1, '0', '0', '0', 0, 0, 0)

    # SUA FUNÇÃO ALTERADA
    def send_command(self, cmd):
        if self.arduino and self.arduino.is_open:
            try:
                self.arduino.write(f"{cmd}\n".encode('utf-8'))
            except SerialException:
                self.handle_disconnection()

    # SUAS FUNÇÕES DE TOGGLE ALTERADAS
    def toggle_system(self, instance):
        new_state = "ON" if not self.system_is_on else "OFF"
        if new_state == "ON":
            self.send_command("SET_TEMP,120.0")
            self.send_command("SET_MOTOR_TEMP,90.0")
        self.send_command(f"SET_STATE,{new_state}")

    def toggle_heater(self, instance):
        """Agora o botão pode desligar o aquecedor mesmo com o sistema ligado."""
        new_state = "ON" if not self.heater_is_on else "OFF"
        self.send_command(f"SET_HEATER,{new_state}")

    def toggle_motor(self, instance):
        """Agora o botão pode desligar o motor mesmo com o sistema ligado (se a temp permitir)."""
        new_state = "ON" if not self.motor_is_on else "OFF"
        self.send_command(f"SET_MOTOR,{new_state}")
    
    def send_param_update(self, name, value):
        cmd_map = {'Velocidade': 'SET_VEL', 'Temp. Alvo': 'SET_TEMP', 'Temp. Motor': 'SET_MOTOR_TEMP'}
        command = cmd_map.get(name)
        if command: self.send_command(f"{command},{value:.2f}")

    # SUA FUNÇÃO ALTERADA
    def read_from_arduino(self, dt):
        if self.arduino and self.arduino.in_waiting > 0:
            try:
                line = self.arduino.readline().decode('utf-8').strip()
                if line.startswith("DATA,"):
                    parts = line.split(',')
                    if len(parts) == 8: self.update_ui(*parts[1:])
            except SerialException:
                self.handle_disconnection()
            except Exception as e:
                print(f"Erro inesperado lendo serial: {e}")

    def update_ui(self, temp, heater_state, motor_state, sys_state, vel, temp_alvo, temp_motor_min):
        try:
            # SUA LÓGICA ALTERADA para resetar o display
            if float(temp) == -1.0 and not self.arduino:
                 self.temp_display.text = '--.-- °C'
            else:
                 self.temp_display.text = f"{float(temp):.2f} °C"

            self.vel_control.param_value = float(vel)
            self.vel_control.update_value_label()
            self.temp_control.param_value = float(temp_alvo)
            self.temp_control.update_value_label()
            self.motor_temp_control.param_value = float(temp_motor_min)
            self.motor_temp_control.update_value_label()

            self.system_is_on = sys_state == '1'
            self.heater_is_on = heater_state == '1'
            self.motor_is_on = motor_state == '1'

            self.master_btn.background_color = self.COLOR_ON if self.system_is_on else self.COLOR_NEUTRAL
            self.master_btn.text = 'Desligar Tudo' if self.system_is_on else 'Ligar Sistema'
            self.heater_btn.background_color = self.COLOR_ON if self.heater_is_on else self.COLOR_OFF
            self.heater_btn.text = 'Desligar Aquecedor' if self.heater_is_on else 'Ligar Aquecedor'
            self.motor_btn.background_color = self.COLOR_ON if self.motor_is_on else self.COLOR_OFF
            self.motor_btn.text = 'Desligar Motor' if self.motor_is_on else 'Ligar Motor'
        except (ValueError, IndexError) as e:
            print(f"Erro ao processar dados do Arduino: {e}")

if __name__ == "__main__":
    FilaBottleApp().run()
