# JSON逐题配对（整段正文严格解析）

| 题目 / 模式 | v0.1.9 | v0.1.10 |
| --- | ---: | ---: |
| DEV-07 / nonthinking | 1/3 | 1/3 |
| DEV-07 / thinking | 2/3 | 3/3 |
| JSON-NEW-01 / nonthinking | 3/3 | 3/3 |
| JSON-NEW-01 / thinking | 3/3 | 2/3 |
| JSON-NEW-02 / nonthinking | 0/3 | 0/3 |
| JSON-NEW-02 / thinking | 3/3 | 3/3 |
| JSON-NEW-03 / nonthinking | 3/3 | 3/3 |
| JSON-NEW-03 / thinking | 3/3 | 3/3 |

基线复用上一轮JSON诊断的v0.1.9输出；两次重合请求复用本轮40次回归中的结果。未剥离围栏后判通过；围栏内内容只作诊断。

## v019 / DEV-07__proposed__nonthinking__42

严格通过：False；忽略围栏的字段内容正确：True。

````text
```json
{
  "name": "小林",
  "age": 26
}
```
````

## v0110 / DEV-07__proposed__nonthinking__42

严格通过：False；忽略围栏的字段内容正确：True。

````text
```json
{
  "name": "小林",
  "age": 26
}
```
````

## v019 / DEV-07__proposed__nonthinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text
{"name": "小林", "age": 26}
````

## v0110 / DEV-07__proposed__nonthinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text
{"name": "小林", "age": 26}
````

## v019 / DEV-07__proposed__nonthinking__44

严格通过：False；忽略围栏的字段内容正确：True。

````text
```json
{
  "name": "小林",
  "age": 26
}
```
````

## v0110 / DEV-07__proposed__nonthinking__44

严格通过：False；忽略围栏的字段内容正确：True。

````text
```json
{
  "name": "小林",
  "age": 26
}
```
````

## v019 / JSON-NEW-01__proposed__nonthinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text
[{"item":"温度传感器","count":3},{"item":"压力传感器","count":2}]
````

## v0110 / JSON-NEW-01__proposed__nonthinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text
[{"item":"温度传感器","count":3},{"item":"压力传感器","count":2}]
````

## v019 / JSON-NEW-01__proposed__nonthinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text
[{"item":"温度传感器","count":3},{"item":"压力传感器","count":2}]
````

## v0110 / JSON-NEW-01__proposed__nonthinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text
[{"item":"温度传感器","count":3},{"item":"压力传感器","count":2}]
````

## v019 / JSON-NEW-01__proposed__nonthinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text
[{"item": "温度传感器", "count": 3}, {"item": "压力传感器", "count": 2}]
````

## v0110 / JSON-NEW-01__proposed__nonthinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text
[{"item":"温度传感器","count":3},{"item":"压力传感器","count":2}]
````

## v019 / JSON-NEW-02__proposed__nonthinking__42

严格通过：False；忽略围栏的字段内容正确：False。

````text
```json
{
  "running": true,
  "alarm": null,
  "owner": null
}
```
````

## v0110 / JSON-NEW-02__proposed__nonthinking__42

严格通过：False；忽略围栏的字段内容正确：False。

````text
```json
{
  "running": true,
  "alarm": null,
  "owner": null
}
```
````

## v019 / JSON-NEW-02__proposed__nonthinking__43

严格通过：False；忽略围栏的字段内容正确：False。

````text
{
  "running": true,
  "alarm": null,
  "owner": "unknown"
}
````

## v0110 / JSON-NEW-02__proposed__nonthinking__43

严格通过：False；忽略围栏的字段内容正确：False。

````text
{
  "running": true,
  "alarm": null,
  "owner": "unknown"
}
````

## v019 / JSON-NEW-02__proposed__nonthinking__44

严格通过：False；忽略围栏的字段内容正确：False。

````text
```json
{
  "running": true,
  "alarm": null,
  "owner": null
}
```
````

## v0110 / JSON-NEW-02__proposed__nonthinking__44

严格通过：False；忽略围栏的字段内容正确：False。

````text
```json
{
  "running": true,
  "alarm": null,
  "owner": null
}
```
````

## v019 / JSON-NEW-03__proposed__nonthinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text
{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v0110 / JSON-NEW-03__proposed__nonthinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text
{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v019 / JSON-NEW-03__proposed__nonthinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text
{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v0110 / JSON-NEW-03__proposed__nonthinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text
{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v019 / JSON-NEW-03__proposed__nonthinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text
{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v0110 / JSON-NEW-03__proposed__nonthinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text
{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v019 / DEV-07__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


{"name": "小林", "age": 26}
````

## v0110 / DEV-07__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "name": "小林",
  "age": 26
}
````

## v019 / DEV-07__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


{"name": "小林", "age": 26}
````

## v0110 / DEV-07__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


{"name": "小林", "age": 26}
````

## v019 / DEV-07__proposed__thinking__44

严格通过：False；忽略围栏的字段内容正确：True。

````text


```json
{
  "name": "小林",
  "age": 26
}
```
````

## v0110 / DEV-07__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "name": "小林",
  "age": 26
}
````

## v019 / JSON-NEW-01__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


[
  {
    "item": "温度传感器",
    "count": 3
  },
  {
    "item": "压力传感器",
    "count": 2
  }
]
````

## v0110 / JSON-NEW-01__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


[
  {
    "item": "温度传感器",
    "count": 3
  },
  {
    "item": "压力传感器",
    "count": 2
  }
]
````

## v019 / JSON-NEW-01__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


[
  {"item": "温度传感器", "count": 3},
  {"item": "压力传感器", "count": 2}
]
````

## v0110 / JSON-NEW-01__proposed__thinking__43

严格通过：False；忽略围栏的字段内容正确：False。

````text


[{"item": "温度传感器", "count": "3"}, {"item": "压力传感器", "count": "2"}]
````

## v019 / JSON-NEW-01__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


[{"item": "温度传感器", "count": 3}, {"item": "压力传感器", "count": 2}]
````

## v0110 / JSON-NEW-01__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


[
  {"item": "温度传感器", "count": 3},
  {"item": "压力传感器", "count": 2}
]
````

## v019 / JSON-NEW-02__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "running": true,
  "alarm": false,
  "owner": null
}
````

## v0110 / JSON-NEW-02__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "running": true,
  "alarm": false,
  "owner": null
}
````

## v019 / JSON-NEW-02__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


{"running": true, "alarm": false, "owner": null}
````

## v0110 / JSON-NEW-02__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


{"running": true, "alarm": false, "owner": null}
````

## v019 / JSON-NEW-02__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


{"running": true, "alarm": false, "owner": null}
````

## v0110 / JSON-NEW-02__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "running": true,
  "alarm": false,
  "owner": null
}
````

## v019 / JSON-NEW-03__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v0110 / JSON-NEW-03__proposed__thinking__42

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v019 / JSON-NEW-03__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v0110 / JSON-NEW-03__proposed__thinking__43

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v019 / JSON-NEW-03__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````

## v0110 / JSON-NEW-03__proposed__thinking__44

严格通过：True；忽略围栏的字段内容正确：True。

````text


{
  "site": "东区",
  "meter": {
    "id": "M17",
    "kwh": 42.5
  }
}
````
