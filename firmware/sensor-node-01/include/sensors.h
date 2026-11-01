#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Adafruit_ISM330DHCX.h>
#include <SparkFun_MMC5983MA_Arduino_Library.h>
#include <driver/i2s.h>
#include "pins.h"

class SensorDrivers {
  Adafruit_BME280 environment;
  Adafruit_ISM330DHCX motion;
  SFE_MMC5983MA magnetic;
public:
  static constexpr int AUDIO_RATE = 32000;
  static constexpr int AUDIO_COUNT = AUDIO_RATE / 20;
  int32_t microphone[AUDIO_COUNT];
  bool begin() {
    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(400000);
    if (!environment.begin(0x76) || !motion.begin_I2C(0x6A) || !magnetic.begin()) return false;
    motion.setAccelRange(LSM6DS_ACCEL_RANGE_2_G);
    motion.setGyroRange(LSM6DS_GYRO_RANGE_250_DPS);
    motion.setAccelDataRate(LSM6DS_RATE_104_HZ);
    motion.setGyroDataRate(LSM6DS_RATE_104_HZ);
    i2s_config_t config = {};
    config.mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_RX);
    config.sample_rate = AUDIO_RATE;
    config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    config.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    config.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    config.dma_buf_count = 8;
    config.dma_buf_len = 256;
    config.use_apll = false;
    i2s_pin_config_t pins = {};
    pins.mck_io_num = I2S_PIN_NO_CHANGE;
    pins.bck_io_num = MIC_BCLK;
    pins.ws_io_num = MIC_LRCLK;
    pins.data_out_num = I2S_PIN_NO_CHANGE;
    pins.data_in_num = MIC_DATA;
    return i2s_driver_install(I2S_NUM_0, &config, 0, nullptr) == ESP_OK && i2s_set_pin(I2S_NUM_0, &pins) == ESP_OK;
  }
  template<typename V, typename A> bool read(V values, A samples) {
    size_t bytes = 0;
    if (i2s_read(I2S_NUM_0, microphone, sizeof(microphone), &bytes, pdMS_TO_TICKS(100)) != ESP_OK || bytes != sizeof(microphone)) return false;
    uint32_t x, y, z;
    magnetic.getMeasurementXYZ(&x, &y, &z);
    // MMC5983MA: 18-bit output, 16384 counts/G; 1 G = 1e-4 T.
    values["M_X"] = (static_cast<double>(x) - 131072) / 16384 * 1e-4;
    values["M_Y"] = (static_cast<double>(y) - 131072) / 16384 * 1e-4;
    values["M_Z"] = (static_cast<double>(z) - 131072) / 16384 * 1e-4;
    sensors_event_t acceleration, gyro, temperature;
    motion.getEvent(&acceleration, &gyro, &temperature);
    values["A_X"] = acceleration.acceleration.x;
    values["A_Y"] = acceleration.acceleration.y;
    values["A_Z"] = acceleration.acceleration.z;
    values["G_X"] = gyro.gyro.x;
    values["G_Y"] = gyro.gyro.y;
    values["G_Z"] = gyro.gyro.z;
    values["Temp"] = environment.readTemperature() + 273.15;
    values["H"] = environment.readHumidity() / 100.;
    values["Pressure"] = environment.readPressure();
    for (int i = 0; i < AUDIO_COUNT; i++) samples.add(static_cast<double>(microphone[i]) / 2147483648.);
    return true;
  }
};
