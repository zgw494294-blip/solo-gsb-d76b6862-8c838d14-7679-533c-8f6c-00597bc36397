# 离线对白字幕分轨 HTTP API

基于 Python 3.12 + FastAPI 实现。服务为离线同步接口，接收 2～3 条屏幕轨道和 1～12 条字幕，在满足时间冲突与锁定约束的前提下，为每条字幕选择轨道，并使同一说话人按时间相邻的字幕换轨次数最少。

## 规则

- 轨道编号从 `1` 开始；请求中通过 `track_count` 指定 `2` 或 `3`。
- 字幕区间为左闭右开：`[start_ms, end_ms)`。
- 时间重叠的字幕不能分配到同一轨；一个区间的结束时间等于另一个区间的开始时间时，可以复用同一轨。
- 同一说话人的字幕区间不能重叠，否则请求非法，返回 `422`。
- `locked_track` 可将字幕锁定到指定轨道；锁定轨道必须在有效轨道编号范围内。
- 锁定后仍无法避开重叠，或同时重叠的字幕数量超过轨道数时，返回无解。
- 优化目标：最小化各说话人按时间相邻两条字幕的换轨次数总和。
- 若多个方案换轨次数相同，选择“按输入顺序排列的轨道号序列”字典序最小的方案。
- 返回的 `assignments` 与请求中的字幕顺序一致。

## 一条命令启动

```bash
docker compose up --build
```

服务监听容器内和宿主机的 **8000 端口**。

- 健康检查：`GET http://localhost:8000/health`
- OpenAPI/Swagger UI：`http://localhost:8000/docs`

停止服务：

```bash
docker compose down
```

## 请求

`POST /assign`

```json
{
  "track_count": 2,
  "subtitles": [
    {
      "id": "a1",
      "speaker": "A",
      "start_ms": 0,
      "end_ms": 1000,
      "locked_track": 1
    }
  ]
}
```

字段说明：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `track_count` | integer | 必填，`2` 或 `3` |
| `subtitles` | array | 必填，1～12 条 |
| `subtitles[].id` | string | 必填，非空且在本次请求中唯一 |
| `subtitles[].speaker` | string | 必填，非空 |
| `subtitles[].start_ms` | integer | 必填，非负 |
| `subtitles[].end_ms` | integer | 必填，非负，且大于 `start_ms` |
| `subtitles[].locked_track` | integer/null | 可选，范围为 `1..track_count` |

非法字段、多余字段、错误类型、重复 ID、同说话人区间重叠、锁定轨道越界等都会返回 HTTP `422`。

## 可执行 HTTP 示例

### 有解：最小化换轨

启动后直接执行：

```bash
curl -sS -X POST http://localhost:8000/assign \
  -H 'Content-Type: application/json' \
  -d '{
    "track_count": 2,
    "subtitles": [
      {"id": "a1", "speaker": "A", "start_ms": 0, "end_ms": 1000, "locked_track": 1},
      {"id": "b1", "speaker": "B", "start_ms": 0, "end_ms": 1000},
      {"id": "a2", "speaker": "A", "start_ms": 1000, "end_ms": 2000},
      {"id": "b2", "speaker": "B", "start_ms": 1000, "end_ms": 2000}
    ]
  }'
```

预期响应：

```json
{
  "solvable": true,
  "assignments": [
    {"id": "a1", "track": 1},
    {"id": "b1", "track": 2},
    {"id": "a2", "track": 1},
    {"id": "b2", "track": 2}
  ],
  "track_changes": 0
}
```

### 无解：两条锁定字幕发生重叠

```bash
curl -sS -X POST http://localhost:8000/assign \
  -H 'Content-Type: application/json' \
  -d '{
    "track_count": 2,
    "subtitles": [
      {"id": "a1", "speaker": "A", "start_ms": 0, "end_ms": 100, "locked_track": 1},
      {"id": "b1", "speaker": "B", "start_ms": 50, "end_ms": 150, "locked_track": 1}
    ]
  }'
```

预期响应：

```json
{
  "solvable": false,
  "assignments": [],
  "track_changes": 0
}
```

### 非法输入：同一说话人字幕重叠

```bash
curl -sS -i -X POST http://localhost:8000/assign \
  -H 'Content-Type: application/json' \
  -d '{
    "track_count": 2,
    "subtitles": [
      {"id": "a1", "speaker": "A", "start_ms": 0, "end_ms": 100},
      {"id": "a2", "speaker": "A", "start_ms": 50, "end_ms": 150}
    ]
  }'
```

预期 HTTP 状态码：`422 Unprocessable Entity`。

## 本地开发与测试

不使用 Docker 时：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

运行测试：

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 项目结构

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py      # FastAPI 路由
│   ├── models.py    # 请求/响应模型与输入校验
│   └── solver.py    # 约束搜索与目标优化
├── tests/
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```
