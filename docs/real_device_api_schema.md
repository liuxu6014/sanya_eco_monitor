# 📡 物联网传感器真实 API 接口与数据结构字典

本文件详细记录了三亚生态监测系统接入的所有底部硬件传感器设备的**真实请求地址**以及**完全物理返回包结构**，以便于后续二次开发与大屏数据全量解构。

---

## 1. WHXPH 物联网底座平台 (环境综合类)
**基础网关 URL:** `https://iot.whxph.com:44300/XPHapiv2`
**接口规范:** `GET /data-n/{device_code}`
**认证机制:** 开放 Token 后端直连

### 1.1 气象综合站 (设备编码: `16110669`)
**请求地址:** `GET https://iot.whxph.com:44300/XPHapiv2/data-n/16110669`

```json
{
  "datetime": "2026-04-11 10:11:45",
  "deviceId": "16110669",
  "name": "16110669",
  "eleLists": [
    { "eName": "风速", "eValue": "0.6", "eUnit": "m/s", "tfValue": "1 级" },
    { "eName": "雨量累计", "eValue": "0.0", "eUnit": "mm" },
    { "eName": "大气温度", "eValue": "20.6", "eUnit": "℃" },
    { "eName": "大气湿度", "eValue": "77.8", "eUnit": "%RH" },
    { "eName": "数字气压", "eValue": "954.5", "eUnit": "hPa" },
    { "eName": "照度", "eValue": "37590.0", "eUnit": "Lux" },
    { "eName": "风向", "eValue": "62", "eUnit": "°", "tfValue": "东北偏东" }
  ]
}
```

### 1.2 土壤养分全能分析仪 (设备编码: `16110670`)
**请求地址:** `GET https://iot.whxph.com:44300/XPHapiv2/data-n/16110670`

```json
{
  "datetime": "2026-04-11 10:11:45",
  "deviceId": "16110670",
  "name": "16110670",
  "eleLists": [
    { "eName": "土壤温度", "eValue": "20.1", "eUnit": "℃" },
    { "eName": "土壤湿度", "eValue": "0.0", "eUnit": "%" },
    { "eName": "电导率", "eValue": "5", "eUnit": "μS/cm" },
    { "eName": "氮离子", "eValue": "0", "eUnit": "mg/KG" },
    { "eName": "磷离子", "eValue": "0", "eUnit": "mg/KG" },
    { "eName": "钾离子", "eValue": "0", "eUnit": "mg/KG" },
    { "eName": "pH值", "eValue": "7.41", "eUnit": "" }
  ]
}
```

### 1.3 坡地水土流失/地表径流雷达 (设备编码: `16132920`)
**请求地址:** `GET https://iot.whxph.com:44300/XPHapiv2/data-n/16132920`

```json
{
  "datetime": "2026-04-11 10:11:46",
  "deviceId": "16132920",
  "name": "16132920",
  "eleLists": [
    { "eName": "流速（m\\s）", "eValue": "0.00", "eUnit": " " },
    { "eName": "雨量累计", "eValue": "0.0", "eUnit": "mm" },
    { "eName": "水位", "eValue": "0.00", "eUnit": "m" },
    { "eName": "流量（m3\\s）", "eValue": "0.00", "eUnit": " " },
    { "eName": "液位压力（kpa）", "eValue": "0.00", "eUnit": " " },
    { "eName": "累计流量", "eValue": "30", "eUnit": "m³" },
    { "eName": "径流（m3\\s）", "eValue": "0.00", "eUnit": " " },
    { "eName": "含沙量（kg\\l）", "eValue": "0.000", "eUnit": " " }
  ]
}
```

### 1.4 农田排水水质污染负荷站 (设备编码: `16116030`)
**请求地址:** `GET https://iot.whxph.com:44300/XPHapiv2/data-n/16116030`

```json
{
  "datetime": "2026-04-11 10:12:24",
  "deviceId": "16116030",
  "name": "16116030",
  "eleLists": [
    { "eName": "PH", "eValue": "7.58", "eUnit": "" },
    { "eName": "电导率", "eValue": "0", "eUnit": "μS/cm" },
    { "eName": "COD", "eValue": "76.46", "eUnit": "mg/L" },
    { "eName": "氨氮", "eValue": "54.01", "eUnit": "mg/L" },
    { "eName": "浊度", "eValue": "9.6", "eUnit": "NTU" },
    { "eName": "溶解氧", "eValue": "7.21", "eUnit": "mg/L" },
    { "eName": "水温", "eValue": "22.8", "eUnit": "℃" },
    { "eName": "总磷", "eValue": "0.201", "eUnit": "mg/L" },
    { "eName": "总氮", "eValue": "32.767", "eUnit": "mg/L" }
  ]
}
```

---

## 2. Zhnl 智慧农业防病虫害平台
**基础网关 URL:** `https://zhnlkj.com/iotSmasrt/http/monitor`
**认证机制:** Token 持久化鉴权 (Header: `Authorization: {token}`)

### 2.1 智能虫情测报灯 (`PBCR48F-340838-0001`) 
**请求地址:** `GET .../getSensorByCode?code=PBCR48F...&collectionTime=YYYY-MM-DD HH:mm:ss,YYYY-MM-DD HH:mm:ss`

```json
{
  "data": {
    "list": [
      {
        "collectionTime": "2026-04-11 02:00:00",
        "detail": "[{\"name\":\"白背飞虱\",\"value\":\"10\"}, {\"name\":\"二化螟\",\"value\":\"3\"}]",
        "insectUrls": "https://zhnl-images.../insect/xxx.jpg",
        "num": "13",
        "deviceId": "PBCR48F-340838-0001"
      }
    ]
  }
}
```

### 2.2 空气孢子捕捉分析仪 (`BZ202411200001`)
**请求地址:** `GET .../getSensorByCode?code=BZ202411200001...`

```json
{
  "data": {
    "list": [
      {
        "collectionTime": "2026-04-11 08:30:00",
        "detail": "[{\"name\":\"稻瘟病孢子\",\"value\":\"42\"}, {\"name\":\"纹枯病孢子\",\"value\":\"18\"}]",
        "sporeUrls": "https://zhnl-images.../spore/xxx.jpg",
        "num": "60",
        "deviceId": "BZ202411200001"
      }
    ]
  }
}
```
