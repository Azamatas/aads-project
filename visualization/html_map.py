# visualization/html_map.py
from __future__ import annotations
from typing import Dict, List
import json
import os
import math

from city.graph import CityGraph
from domain.models import Plan, Vehicle
from algorithms.a_star import astar_shortest_path


def _compute_screen_coords(
    graph: CityGraph,
    width: int = 900,
    height: int = 700,
    padding: int = 40,
) -> Dict[str, Dict[str, float]]:
    xs = [n.x for n in graph.nodes.values()]
    ys = [n.y for n in graph.nodes.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    span_x = max_x - min_x or 1.0
    span_y = max_y - min_y or 1.0

    scale_x = (width - 2 * padding) / span_x
    scale_y = (height - 2 * padding) / span_y

    coords: Dict[str, Dict[str, float]] = {}
    for nid, node in graph.nodes.items():
        sx = padding + (node.x - min_x) * scale_x
        sy = padding + (max_y - node.y) * scale_y  # инверсия Y
        coords[nid] = {"x": sx, "y": sy}
    return coords


def _build_full_route_nodes(
    graph: CityGraph,
    plan: Plan,
    vehicles: List[Vehicle],
) -> Dict[str, List[str]]:
    """
    Для каждой машины строим последовательность узлов:
    старт -> все заказы -> депо.
    """
    result: Dict[str, List[str]] = {}
    v_index = {v.id: v for v in vehicles}

    for vid, route in plan.routes.items():
        v = v_index[vid]
        cur = v.start_node
        nodes_seq: List[str] = [cur]

        for req in route.stops:
            path, _ = astar_shortest_path(graph, cur, req.node)
            if path is None:
                continue
            nodes_seq.extend(path[1:])
            cur = req.node

        if route.stops:
            path, _ = astar_shortest_path(graph, cur, plan.depot)
            if path is not None:
                nodes_seq.extend(path[1:])

        result[vid] = nodes_seq
    return result


def export_plan_to_html(
    graph: CityGraph,
    plans_by_algo: Dict[str, Plan],
    vehicles: List[Vehicle],
    output_path: str = "output/campus_routes.html",
) -> None:
    """
    Генерирует HTML, в котором можно переключать алгоритм (Greedy / Monte Carlo)
    через выпадающий список. Для каждого алгоритма:

      - свои маршруты машин,
      - свои delivery-узлы,
      - своя анимация.

    Ноды-доставки сразу окрашены в цвет машины; после визита становятся больше.
    Добавлен таймер анимации (t = ... s), который сбрасывается при смене алгоритма.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    screen_coords = _compute_screen_coords(graph)

    # предполагаем, что у всех планов один и тот же depot
    any_plan = next(iter(plans_by_algo.values()))
    depot = any_plan.depot

    algorithms_payload = []

    for algo_name, plan in plans_by_algo.items():
        full_routes = _build_full_route_nodes(graph, plan, vehicles)

        delivery_nodes_set = set()
        for route in plan.routes.values():
            for req in route.stops:
                delivery_nodes_set.add(req.node)

        deliveries_meta = []
        for vid, node_seq in full_routes.items():
            cum = 0.0
            seen_for_this_route = set()
            for i in range(len(node_seq) - 1):
                a_id = node_seq[i]
                b_id = node_seq[i + 1]
                a = screen_coords[a_id]
                b = screen_coords[b_id]
                seg_len = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
                cum += seg_len
                if b_id in delivery_nodes_set and b_id not in seen_for_this_route:
                    deliveries_meta.append(
                        {"vehicle_id": vid, "node_id": b_id, "arrival_dist": cum}
                    )
                    seen_for_this_route.add(b_id)

        routes_payload = [
            {
                "vehicle_id": vid,
                "nodes": [
                    {
                        "id": nid,
                        "x": screen_coords[nid]["x"],
                        "y": screen_coords[nid]["y"],
                    }
                    for nid in nodes
                ],
            }
            for vid, nodes in full_routes.items()
        ]

        algorithms_payload.append({
            "id": algo_name,
            "label": algo_name,
            "routes": routes_payload,
            "delivery_nodes": list(delivery_nodes_set),
            "deliveries": deliveries_meta,
        })

    data = {
        "nodes": [
            {
                "id": nid,
                "x": screen_coords[nid]["x"],
                "y": screen_coords[nid]["y"],
            }
            for nid in graph.nodes.keys()
        ],
        "edges": [
            {"src": e.src, "dst": e.dst}
            for nid in graph.nodes.keys()
            for e in graph.neighbors(nid)
        ],
        "depot": depot,
        "algorithms": algorithms_payload,
    }

    json_data = json.dumps(data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>City routes</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      background: #020617;
      color: #e5e7eb;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }}
    #card {{
      background: #020617;
      border-radius: 18px;
      box-shadow: 0 18px 40px rgba(0,0,0,0.6);
      padding: 16px 20px 24px;
      border: 1px solid #1f2937;
      min-width: 960px;
    }}
    #title {{
      margin: 0 0 4px 0;
      font-size: 18px;
      font-weight: 600;
    }}
    #subtitle {{
      margin: 0 0 10px 0;
      font-size: 13px;
      color: #9ca3af;
    }}
    #controls {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
      font-size: 13px;
      justify-content: space-between;
    }}
    #algo-box {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    #algo-select {{
      background: #020617;
      color: #e5e7eb;
      border-radius: 6px;
      border: 1px solid #374151;
      padding: 4px 8px;
      font-size: 13px;
    }}
    #timer {{
      font-size: 13px;
      color: #e5e7eb;
      font-variant-numeric: tabular-nums;
    }}
    #legend {{
      display: flex;
      gap: 12px;
      margin-bottom: 8px;
      font-size: 12px;
      flex-wrap: wrap;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}
    .legend-swatch {{
      width: 14px;
      height: 3px;
      border-radius: 999px;
    }}
    canvas {{
      border-radius: 12px;
      background: #020617;
      border: 1px solid #1f2937;
      cursor: grab;
    }}
    canvas:active {{
      cursor: grabbing;
    }}
  </style>
</head>
<body>
<div id="card">
  <h1 id="title">Constructor University — Delivery Routes</h1>
  <p id="subtitle">Choose algorithm, drag to pan, scroll to zoom</p>
  <div id="controls">
    <div id="algo-box">
      <span>Algorithm:</span>
      <select id="algo-select"></select>
    </div>
    <div id="timer">t = 0.0 s</div>
  </div>
  <div id="legend"></div>
  <canvas id="map" width="900" height="700"></canvas>
</div>

<script>
  const DATA = {json_data};

  const colors = [
    "#f97316", "#22c55e", "#3b82f6", "#e11d48",
    "#a855f7", "#14b8a6", "#facc15"
  ];

  const dashPatterns = [
    [],            // solid
    [10, 6],       // long dash
    [4, 4],        // medium dash
    [14, 4, 2, 4], // dash-dot
    [2, 6],        // dotted-ish
    [1, 3],        // fine dots
    [12, 3, 3, 3], // long-short pattern
  ];

  const canvas = document.getElementById("map");
  const ctx = canvas.getContext("2d");
  const legendEl = document.getElementById("legend");
  const algoSelect = document.getElementById("algo-select");
  const timerEl = document.getElementById("timer");

  let offsetX = 0;
  let offsetY = 0;
  let scale = 1.0;

  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;

  let currentAlgoIndex = 0;
  let ROUTES = [];
  let DELIVERY_NODES = new Set();
  let deliveries = [];
  let visitedDeliveryNodes = new Set();
  let deliveryColorByNode = new Map();
  let lastTime = null;
  let simTime = 0.0; // виртуальное время анимации (секунды)

  function updateTimerLabel() {{
    if (!timerEl) return;
    timerEl.textContent = "t = " + simTime.toFixed(1) + " s";
  }}

  function rebuildLegend() {{
    legendEl.innerHTML = "";
    ROUTES.forEach((route) => {{
      const item = document.createElement("div");
      item.className = "legend-item";
      const swatch = document.createElement("div");
      swatch.className = "legend-swatch";
      swatch.style.backgroundColor = route.color;
      const label = document.createElement("span");
      label.textContent = route.vehicle_id;
      item.appendChild(swatch);
      item.appendChild(label);
      legendEl.appendChild(item);
    }});
  }}

  function initAlgorithm(index) {{
    currentAlgoIndex = index;
    const algo = DATA.algorithms[index];

    // 1) маршруты
    ROUTES = algo.routes.map((route, idx) => {{
      const pts = route.nodes;
      const segments = [];
      let totalLen = 0;
      for (let i = 0; i < pts.length - 1; i++) {{
        const a = pts[i];
        const b = pts[i + 1];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy);
        if (len > 0) {{
          segments.push({{ a, b, len }});
          totalLen += len;
        }}
      }}
      return {{
        vehicle_id: route.vehicle_id,
        color: colors[idx % colors.length],
        segments,
        totalLen,
        dist: 0,
        finished: false,
      }};
    }});

    // 2) delivery-структуры
    DELIVERY_NODES = new Set(algo.delivery_nodes || []);
    deliveries = (algo.deliveries || []).map(
      d => Object.assign({{ served: false }}, d)
    );
    visitedDeliveryNodes = new Set();
    deliveryColorByNode = new Map();

    // ноды сразу красятся в цвет машины
    for (const d of deliveries) {{
      const route = ROUTES.find(r => r.vehicle_id === d.vehicle_id);
      if (route && !deliveryColorByNode.has(d.node_id)) {{
        deliveryColorByNode.set(d.node_id, route.color);
      }}
    }}

    // сбрасываем таймер и время
    simTime = 0.0;
    lastTime = null;
    updateTimerLabel();

    rebuildLegend();
    draw();
    requestAnimationFrame(animate);
  }}

  function draw() {{
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);

    // фон
    ctx.fillStyle = "#020617";
    ctx.fillRect(-2000, -2000, 4000, 4000);

    // серые дороги
    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (const edge of DATA.edges) {{
      const src = DATA.nodes.find(n => n.id === edge.src);
      const dst = DATA.nodes.find(n => n.id === edge.dst);
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(dst.x, dst.y);
    }}
    ctx.stroke();

    // цветные "следы" машин
    ROUTES.forEach((route, idx) => {{
      if (route.segments.length === 0 || route.dist <= 0) return;

      let remaining = route.dist;

      ctx.save();
      ctx.strokeStyle = route.color;
      ctx.lineWidth = 6;
      ctx.setLineDash(dashPatterns[idx % dashPatterns.length]);

      ctx.beginPath();
      let started = false;

      for (const seg of route.segments) {{
        if (remaining <= 0) break;

        const a = seg.a;
        const b = seg.b;
        const len = seg.len;
        const drawLen = Math.min(len, remaining);
        const t = len === 0 ? 0 : drawLen / len;

        const sx = a.x;
        const sy = a.y;
        const ex = a.x + (b.x - a.x) * t;
        const ey = a.y + (b.y - a.y) * t;

        if (!started) {{
          ctx.moveTo(sx, sy);
          started = true;
        }} else {{
          ctx.lineTo(sx, sy);
        }}
        ctx.lineTo(ex, ey);

        remaining -= drawLen;
      }}

      ctx.stroke();
      ctx.restore();
    }});

    // узлы
    for (const node of DATA.nodes) {{
      const nodeId = node.id;
      const isDepot = (nodeId === DATA.depot);
      const isDelivery = DELIVERY_NODES.has(nodeId);
      const isVisited = visitedDeliveryNodes.has(nodeId);

      let fillColor = "#e5e7eb";
      let radius = 3;

      if (isDepot) {{
        fillColor = "#22c55e";
        radius = 6;
      }} else if (isDelivery) {{
        const vehicleColor = deliveryColorByNode.get(nodeId) || "#ef4444";
        if (!isVisited) {{
          fillColor = vehicleColor;
          radius = 6;
        }} else {{
          fillColor = vehicleColor;
          radius = 8;
        }}
      }}

      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = fillColor;
      ctx.fill();

      if (isDelivery) {{
        ctx.lineWidth = 1;
        ctx.strokeStyle = "#111827";
        ctx.stroke();
      }}

      ctx.fillStyle = "#9ca3af";
      ctx.font = "10px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(node.id, node.x, node.y - (radius + 4));
    }}

    // машинки
    for (const route of ROUTES) {{
      if (route.segments.length === 0 || route.totalLen === 0) continue;

      let d = route.dist;
      if (d <= 0) continue;

      for (const seg of route.segments) {{
        if (d <= seg.len) {{
          const t = seg.len === 0 ? 0 : d / seg.len;
          const x = seg.a.x + (seg.b.x - seg.a.x) * t;
          const y = seg.a.y + (seg.b.y - seg.a.y) * t;

          ctx.beginPath();
          ctx.fillStyle = route.color;
          ctx.arc(x, y, 8, 0, Math.PI * 2);
          ctx.fill();
          break;
        }}
        d -= seg.len;
      }}
    }}

    ctx.restore();
  }}

  // Панорамирование
  canvas.addEventListener("mousedown", (e) => {{
    isDragging = true;
    dragStartX = e.clientX - offsetX;
    dragStartY = e.clientY - offsetY;
  }});
  window.addEventListener("mouseup", () => {{
    isDragging = false;
  }});
  canvas.addEventListener("mousemove", (e) => {{
    if (!isDragging) return;
    offsetX = e.clientX - dragStartX;
    offsetY = e.clientY - dragStartY;
    draw();
  }});

  // Зум колесиком
  canvas.addEventListener("wheel", (e) => {{
    e.preventDefault();
    const zoomFactor = 1.05;
    const mouseX = (e.offsetX - offsetX) / scale;
    const mouseY = (e.offsetY - offsetY) / scale;

    if (e.deltaY < 0) {{
      scale *= zoomFactor;
    }} else {{
      scale /= zoomFactor;
    }}

    offsetX = e.offsetX - mouseX * scale;
    offsetY = e.offsetY - mouseY * scale;
    draw();
  }}, {{ passive: false }});

  // заполнение селекта алгоритмов
  DATA.algorithms.forEach((algo, idx) => {{
    const opt = document.createElement("option");
    opt.value = String(idx);
    opt.textContent = algo.label;
    algoSelect.appendChild(opt);
  }});

  algoSelect.addEventListener("change", (e) => {{
    const idx = parseInt(e.target.value, 10) || 0;
    initAlgorithm(idx);
  }});

  // Анимация: один проход для текущего алгоритма
  const SPEED = 80; // пикселей в секунду

  function animate(timestamp) {{
    if (lastTime === null) {{
      lastTime = timestamp;
    }}
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;

    let allFinished = true;

    for (const route of ROUTES) {{
      if (route.finished || route.totalLen === 0) continue;

      route.dist += SPEED * dt;
      if (route.dist >= route.totalLen) {{
        route.dist = route.totalLen;
        route.finished = true;
      }} else {{
        allFinished = false;
      }}
    }}

    // обновляем статусы доставок
    for (const d of deliveries) {{
      if (d.served) continue;
      const route = ROUTES.find(r => r.vehicle_id === d.vehicle_id);
      if (!route) continue;
      if (route.dist >= d.arrival_dist) {{
        d.served = true;
        visitedDeliveryNodes.add(d.node_id);
      }}
    }}

    // обновляем виртуальное время и таймер
    simTime += dt;
    updateTimerLabel();

    draw();

    if (!allFinished) {{
      requestAnimationFrame(animate);
    }}
  }}

  // старт: первый алгоритм
  if (DATA.algorithms.length > 0) {{
    algoSelect.value = "0";
    initAlgorithm(0);
  }}
</script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML map exported to {os.path.abspath(output_path)}")
