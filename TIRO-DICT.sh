'EGM_OUT_SENS_23_VAR_32' - 'SENS_Digil2_TC_F12A_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_33' - 'SENS_Digil2_TC_F12A_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_34' - 'SENS_Digil2_TC_F12B_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_35' - 'SENS_Digil2_TC_F12B_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_36' - 'SENS_Digil2_TC_F4A_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_37' - 'SENS_Digil2_TC_F4A_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_38' - 'SENS_Digil2_TC_F4B_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_39' - 'SENS_Digil2_TC_F4B_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_40' - 'SENS_Digil2_TC_F8A_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_41' - 'SENS_Digil2_TC_F8A_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_42' - 'SENS_Digil2_TC_F8B_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_43' - 'SENS_Digil2_TC_F8B_L2_IN_ALARM'


⚡ SENSORI DI TIRO - METRICHE EIT
python# Fase 4
'EIT_LOAD_04_A_L1' -> 'SENS_Digil2_TC_F4A_L1'  # min, avg, max
'EIT_LOAD_04_A_L2' -> 'SENS_Digil2_TC_F4A_L2'  # min, avg, max
'EIT_LOAD_04_B_L1' -> 'SENS_Digil2_TC_F4B_L1'  # min, avg, max
'EIT_LOAD_04_B_L2' -> 'SENS_Digil2_TC_F4B_L2'  # min, avg, max

# Fase 8
'EIT_LOAD_08_A_L1' -> 'SENS_Digil2_TC_F8A_L1'  # min, avg, max
'EIT_LOAD_08_A_L2' -> 'SENS_Digil2_TC_F8A_L2'  # min, avg, max
'EIT_LOAD_08_B_L1' -> 'SENS_Digil2_TC_F8B_L1'  # min, avg, max
'EIT_LOAD_08_B_L2' -> 'SENS_Digil2_TC_F8B_L2'  # min, avg, max

# Fase 12
'EIT_LOAD_12_A_L1' -> 'SENS_Digil2_TC_F12A_L1'  # min, avg, max
'EIT_LOAD_12_A_L2' -> 'SENS_Digil2_TC_F12A_L2'  # min, avg, max
'EIT_LOAD_12_B_L1' -> 'SENS_Digil2_TC_F12B_L1'  # min, avg, max
'EIT_LOAD_12_B_L2' -> 'SENS_Digil2_TC_F12B_L2'  # min, avg, max
⚡ SENSORI TIRO - ALLARMI ISTANTANEI EGM
python'EGM_OUT_SENS_23_VAR_32' -> 'SENS_Digil2_TC_F12A_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_33' -> 'SENS_Digil2_TC_F12A_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_34' -> 'SENS_Digil2_TC_F12B_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_35' -> 'SENS_Digil2_TC_F12B_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_36' -> 'SENS_Digil2_TC_F4A_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_37' -> 'SENS_Digil2_TC_F4A_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_38' -> 'SENS_Digil2_TC_F4B_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_39' -> 'SENS_Digil2_TC_F4B_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_40' -> 'SENS_Digil2_TC_F8A_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_41' -> 'SENS_Digil2_TC_F8A_L2_IN_ALARM'
'EGM_OUT_SENS_23_VAR_42' -> 'SENS_Digil2_TC_F8B_L1_IN_ALARM'
'EGM_OUT_SENS_23_VAR_43' -> 'SENS_Digil2_TC_F8B_L2_IN_ALARM'
📦 JUNCTION BOX - ACCELEROMETRI EIT
python'EIT_ACCEL_X' -> 'SENS_Digil2_Acc_X'  # min, avg, max
'EIT_ACCEL_Y' -> 'SENS_Digil2_Acc_Y'  # min, avg, max
'EIT_ACCEL_Z' -> 'SENS_Digil2_Acc_Z'  # min, avg, max
📦 JUNCTION BOX - INCLINOMETRI
python# Metriche EIT
'EIT_INCLIN_X' -> 'SENS_Digil2_Inc_X'  # min, avg, max
'EIT_INCLIN_Y' -> 'SENS_Digil2_Inc_Y'  # min, avg, max

# Allarmi EGM
'EGM_OUT_SENS_23_VAR_30' -> 'SENS_Digil2_Inc_X_IN_ALARM'
'EGM_OUT_SENS_23_VAR_31' -> 'SENS_Digil2_Inc_Y_IN_ALARM'
🌤️ STAZIONE METEO
python# Basandomi sul primo JSON, le metriche meteo dovrebbero essere:
'EIT_WINDVEL'     -> 'SENS_Digil2_Wind_Speed'     # min, avg, max, value
'EIT_WINDDIR1'    -> 'SENS_Digil2_Wind_Dir'       # value
'EIT_HUMIDITY'    -> 'SENS_Digil2_Humidity'       # value
'EIT_TEMPERATURE' -> 'SENS_Digil2_Temperature'    # value
'EIT_PIROMETER'   -> 'SENS_Digil2_Pirometer'      # value

# Extra
'WIND_AGGREGATE'  -> Aggregato vento (composite)
🔋 SISTEMA BATTERIA E ALIMENTAZIONE
python# Mappature probabili (non presenti nei MongoDB ma dedotte dal primo JSON)
'EIT_BATTERY_LEVEL'    -> 'SENS_Digil2_BatteryLevel_Percent'
'EIT_BATTERY_STATE'    -> 'SENS_Digil2_BatteryState_Percent'
'EIT_BATTERY_VOLT'     -> 'SENS_Digil2_Battery_VOLT'
'EIT_BATTERY_AMPERE'   -> 'SENS_Digil2_BatteryOut_AMPERE'
'EIT_BATTERY_TEMP'     -> 'SENS_Digil2_Batt_Temp_1'
'EIT_SOLAR_VOLTAGE'    -> 'SENS_Digil2_SolarPanelVoltage'
'EIT_SOLAR_CURRENT'    -> 'SENS_Digil2_SolarPanelCurrent'
'EIT_MPPT_STATUS'      -> 'SENS_Digil2_MPPTStatus'
'EIT_ENERGY_CONS'      -> 'SENS_Digil2_ConsumptionEnergy'
'EIT_ENERGY_TOTAL'     -> 'SENS_Digil2_TotalConsumptionEnergy'
📡 COMUNICAZIONE
python'EGM_OUT_SENS_23_VAR_7' -> 'SENS_Digil2_Channel'  # value (string: "LTE")
'EIT_LTE_SIGNAL'        -> 'SENS_Digil2_LtePowerSignal'
'EIT_NBIOT_SIGNAL'      -> 'SENS_Digil2_NBIoTPowerSignal'
🌡️ TEMPERATURE CABINET
python'EIT_TEMP_CABIN'  -> 'SENS_Digil2_TmpInCabin'
'EIT_TEMP_DEVICE' -> 'SENS_Digil2_TmpDevice'
🔔 ALLARMI DIAGNOSTICA EAM
python# Sensori Tiro - Pattern: EAM_OUT_ALG_19_VAR_XX
'EAM_OUT_ALG_19_VAR_13' -> 'ALG_Digil2_Alm_Min_TC_F4A_L1'
'EAM_OUT_ALG_19_VAR_14' -> 'ALG_Digil2_Alm_Max_TC_F4A_L1'
'EAM_OUT_ALG_19_VAR_15' -> 'ALG_Digil2_Alm_Min_TC_F4B_L1'
'EAM_OUT_ALG_19_VAR_16' -> 'ALG_Digil2_Alm_Max_TC_F4B_L1'
'EAM_OUT_ALG_19_VAR_17' -> 'ALG_Digil2_Alm_Min_TC_F8A_L1'
'EAM_OUT_ALG_19_VAR_18' -> 'ALG_Digil2_Alm_Max_TC_F8A_L1'
'EAM_OUT_ALG_19_VAR_19' -> 'ALG_Digil2_Alm_Min_TC_F8B_L1'
'EAM_OUT_ALG_19_VAR_20' -> 'ALG_Digil2_Alm_Max_TC_F8B_L1'
'EAM_OUT_ALG_19_VAR_21' -> 'ALG_Digil2_Alm_Min_TC_F12A_L1'
'EAM_OUT_ALG_19_VAR_22' -> 'ALG_Digil2_Alm_Max_TC_F12A_L1'
'EAM_OUT_ALG_19_VAR_23' -> 'ALG_Digil2_Alm_Min_TC_F12B_L1'
'EAM_OUT_ALG_19_VAR_24' -> 'ALG_Digil2_Alm_Max_TC_F12B_L1'
'EAM_OUT_ALG_19_VAR_25' -> 'ALG_Digil2_Alm_Min_TC_F4A_L2'
'EAM_OUT_ALG_19_VAR_26' -> 'ALG_Digil2_Alm_Max_TC_F4A_L2'
'EAM_OUT_ALG_19_VAR_27' -> 'ALG_Digil2_Alm_Min_TC_F4B_L2'
'EAM_OUT_ALG_19_VAR_28' -> 'ALG_Digil2_Alm_Max_TC_F4B_L2'
'EAM_OUT_ALG_19_VAR_29' -> 'ALG_Digil2_Alm_Min_TC_F8A_L2'
'EAM_OUT_ALG_19_VAR_30' -> 'ALG_Digil2_Alm_Max_TC_F8A_L2'
'EAM_OUT_ALG_19_VAR_31' -> 'ALG_Digil2_Alm_Min_TC_F8B_L2'
'EAM_OUT_ALG_19_VAR_32' -> 'ALG_Digil2_Alm_Max_TC_F8B_L2'
'EAM_OUT_ALG_19_VAR_33' -> 'ALG_Digil2_Alm_Min_TC_F12A_L2'
'EAM_OUT_ALG_19_VAR_34' -> 'ALG_Digil2_Alm_Max_TC_F12A_L2'
'EAM_OUT_ALG_19_VAR_35' -> 'ALG_Digil2_Alm_Min_TC_F12B_L2'
'EAM_OUT_ALG_19_VAR_36' -> 'ALG_Digil2_Alm_Max_TC_F12B_L2'

# Altri Allarmi
'EAM_OUT_ALG_19_VAR_4'  -> 'ALG_Digil2_Alm_Accelerometro'
'EAM_OUT_ALG_19_VAR_5'  -> 'ALG_Digil2_Warn_Incl'
'EAM_OUT_ALG_19_VAR_6'  -> 'ALG_Digil2_Alm_Incl'
'EAM_OUT_ALG_19_VAR_10' -> 'ALG_Digil2_Alm_Low_Temp'
'EAM_OUT_ALG_19_VAR_12' -> 'ALG_Digil2_Alm_High_Temp_Battery'
'EAM_OUT_ALG_19_VAR_37' -> 'ALG_Digil2_Alm_Low_Batt'
📊 METRICHE DI QUALITÀ
python'QC'  -> Quality Control (1 = OK)
'NQC' -> Non-Quality Control (contatore errori)
'TIMESTAMP' -> Timestamp della misura