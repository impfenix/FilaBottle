#include <EEPROM.h>
#include <math.h>

// Pinos
#define TERMISTOR_PIN A5
#define RELE_PIN 9
#define STEP_PIN 3
#define DIR_PIN 4

// Constantes do termistor
const float R_SERIE = 100000.0;
const float VREF = 5.0;
const int ADC_RESOLUCAO = 1023;
const float T0 = 298.15;
const float BETA = 3950.0;
const float R0 = 100000.0;
const float CORRECAO = 0.0;

// Variáveis de controle (serão carregadas da EEPROM)
float TEMP_ALVO_MAX;     // Ex: 260.0
float TEMP_ALVO_MIN;     // Ex: 255.0
float TEMP_MIN_MOTOR;    // Ex: 180.0
float VELOCIDADE_MM_S;   // Ex: 40.0

const int PASSOS_POR_REV = 200;
const float PASSO_DO_FUSO = 8.0;
const float MICROSTEPS = 16.0;
float passosPorMM;
unsigned long INTERVALO_PULSOS;

bool aquecedorLigado = false;
bool motorAtivo = false;

void salvarConfiguracoes() {
  EEPROM.put(0, VELOCIDADE_MM_S);
  EEPROM.put(4, TEMP_ALVO_MAX);
  EEPROM.put(8, TEMP_MIN_MOTOR);
}

void carregarConfiguracoes() {
  EEPROM.get(0, VELOCIDADE_MM_S);
  EEPROM.get(4, TEMP_ALVO_MAX);
  EEPROM.get(8, TEMP_MIN_MOTOR);

  if (isnan(VELOCIDADE_MM_S) || VELOCIDADE_MM_S < 1 || VELOCIDADE_MM_S > 100) VELOCIDADE_MM_S = 40.0;
  if (isnan(TEMP_ALVO_MAX) || TEMP_ALVO_MAX < 100 || TEMP_ALVO_MAX > 300) TEMP_ALVO_MAX = 260.0;
  if (isnan(TEMP_MIN_MOTOR) || TEMP_MIN_MOTOR < 100 || TEMP_MIN_MOTOR > 300) TEMP_MIN_MOTOR = 180.0;

  TEMP_ALVO_MIN = TEMP_ALVO_MAX - 5;
  passosPorMM = (PASSOS_POR_REV * MICROSTEPS) / PASSO_DO_FUSO;
  INTERVALO_PULSOS = (1000000.0 / (VELOCIDADE_MM_S * passosPorMM));
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(100);

  pinMode(RELE_PIN, OUTPUT);
  digitalWrite(RELE_PIN, HIGH); // Desliga o aquecedor (relé NF: HIGH = DESLIGADO)

  pinMode(TERMISTOR_PIN, INPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(DIR_PIN, HIGH);

  carregarConfiguracoes();
  Serial.println("Sistema iniciado.");
}

float calcularTemperatura(int leituraADC) {
  if (leituraADC <= 0 || leituraADC >= ADC_RESOLUCAO) return -1;
  float V = (float)leituraADC * VREF / ADC_RESOLUCAO;
  float Rt = R_SERIE * ((VREF / V) - 1.0);
  if (Rt <= 0) return -1;
  float tempK = 1.0 / ((1.0 / T0) + (1.0 / BETA) * log(Rt / R0));
  return tempK - 273.15 + CORRECAO;
}

void controlarRele(float temperatura) {
  if (temperatura == -1) return;

  if (!aquecedorLigado && temperatura <= TEMP_ALVO_MIN) {
    digitalWrite(RELE_PIN, LOW); // Liga o aquecedor (relé NF: LOW = LIGADO)
    aquecedorLigado = true;
    Serial.println("Aquecedor LIGADO: Temperatura abaixo do mínimo.");
  } else if (aquecedorLigado && temperatura >= TEMP_ALVO_MAX) {
    digitalWrite(RELE_PIN, HIGH); // Desliga o aquecedor (relé NF: HIGH = DESLIGADO)
    aquecedorLigado = false;
    Serial.println("Aquecedor DESLIGADO: Temperatura acima do máximo.");
  }
}

void controlarMotor(float temperatura) {
  motorAtivo = temperatura >= TEMP_MIN_MOTOR;
  if (motorAtivo) {
    static unsigned long ultimaEtapa = 0;
    if (micros() - ultimaEtapa >= INTERVALO_PULSOS) {
      ultimaEtapa = micros();
      digitalWrite(STEP_PIN, HIGH);
      delayMicroseconds(10);
      digitalWrite(STEP_PIN, LOW);
    }
  }
}

void processarComandoSerial() {
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    if (comando.startsWith("SET")) {
      int primeiro = comando.indexOf(',');
      int segundo = comando.indexOf(',', primeiro + 1);
      int terceiro = comando.indexOf(',', segundo + 1);

      if (primeiro > 0 && segundo > primeiro && terceiro > segundo) {
        VELOCIDADE_MM_S = comando.substring(primeiro + 1, segundo).toFloat();
        TEMP_ALVO_MAX = comando.substring(segundo + 1, terceiro).toFloat();
        TEMP_MIN_MOTOR = comando.substring(terceiro + 1).toFloat();
        TEMP_ALVO_MIN = TEMP_ALVO_MAX - 5;
        passosPorMM = (PASSOS_POR_REV * MICROSTEPS) / PASSO_DO_FUSO;
        INTERVALO_PULSOS = (1000000.0 / (VELOCIDADE_MM_S * passosPorMM));
        salvarConfiguracoes();
        Serial.println("Configurações atualizadas.");
      }
    }
  }
}

void loop() {
  processarComandoSerial();

  int leituraADC = analogRead(TERMISTOR_PIN);
  float temperatura = calcularTemperatura(leituraADC);

  controlarRele(temperatura);
  controlarMotor(temperatura);

  if (temperatura != -1) {
    Serial.print("Temperatura: ");
    Serial.print(temperatura, 2);
    Serial.println(" °C");
  }

  delay(500); // frequência de leitura do termistor
}
