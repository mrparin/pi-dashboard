"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import SensorIcon, { type SensorIconType } from "./SensorIcon";

type Point = { timestamp_ms: number; value: number };
type Series = { label: string; unit: string; color: string; points: Point[] };
type HistoryMap = Record<string, Point[]>;
type HoverState = { timestamp: number; x: number; values: { label: string; unit: string; color: string; value: number; y: number }[] };

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";
const chartWidth = 1500;
const chartHeight = 310;
const plot = { left: 58, right: 28, top: 24, bottom: 44 };

function formatValue(value: number) {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
}

function LineChart({ title, period, series, icon, controls = false }: { title: string; period: string; series: Series[]; icon: SensorIconType; controls?: boolean }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<HoverState | null>(null);
  const gradientPrefix = useId().replace(/:/g, "");
  const points = series.flatMap((item) => item.points);
  const timeMin = points.length ? Math.min(...points.map((point) => point.timestamp_ms)) : Date.now();
  const timeMax = points.length ? Math.max(...points.map((point) => point.timestamp_ms)) : Date.now();

  useEffect(() => {
    if (controls && scroller.current) scroller.current.scrollLeft = scroller.current.scrollWidth;
  }, [controls, points.length]);

  function move(direction: -1 | 1) {
    scroller.current?.scrollBy({ left: direction * 520, behavior: "smooth" });
  }

  if (!points.length) return <article className="trend-card"><header className="trend-card-head"><div><p className="eyebrow">{period}</p><h3>{title}</h3></div></header><p className="chart-empty">ยังไม่มีข้อมูลในช่วงเวลานี้</p></article>;

  const x = (timestamp: number) => plot.left + ((timestamp - timeMin) / Math.max(1, timeMax - timeMin)) * (chartWidth - plot.left - plot.right);
  const yFor = (item: Series, value: number) => {
    const values = item.points.map((point) => point.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = Math.max((max - min) * 0.12, 0.05);
    return plot.top + (1 - (value - (min - padding)) / Math.max(0.0001, max + padding - (min - padding))) * (chartHeight - plot.top - plot.bottom);
  };
  const pathFor = (item: Series) => {
    return item.points.map((point, index) => `${index ? "L" : "M"}${x(point.timestamp_ms).toFixed(1)},${yFor(item, point.value).toFixed(1)}`).join(" ");
  };
  const areaFor = (item: Series) => {
    if (!item.points.length) return "";
    const line = pathFor(item);
    const firstX = x(item.points[0].timestamp_ms).toFixed(1);
    const lastX = x(item.points[item.points.length - 1].timestamp_ms).toFixed(1);
    const baseline = chartHeight - plot.bottom;
    return `${line} L${lastX},${baseline} L${firstX},${baseline} Z`;
  };

  function showNearest(event: ReactMouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerX = Math.min(chartWidth - plot.right, Math.max(plot.left, (event.clientX - rect.left) * chartWidth / rect.width));
    const targetTime = timeMin + ((pointerX - plot.left) / (chartWidth - plot.left - plot.right)) * (timeMax - timeMin);
    const nearest = (item: Series) => item.points.reduce((best, point) => Math.abs(point.timestamp_ms - targetTime) < Math.abs(best.timestamp_ms - targetTime) ? point : best);
    const anchor = nearest(series[0]);
    setHover({ timestamp: anchor.timestamp_ms, x: x(anchor.timestamp_ms), values: series.map((item) => {
      const point = nearest(item);
      return { label: item.label, unit: item.unit, color: item.color, value: point.value, y: yFor(item, point.value) };
    }) });
  }

  return <article className="trend-card">
    <header className="trend-card-head"><div className="trend-title"><SensorIcon type={icon} /><div><p className="eyebrow">{period}</p><h3>{title}</h3></div></div>{controls && <div className="chart-controls"><button onClick={() => move(-1)} aria-label="เลื่อนกราฟไปทางซ้าย">←</button><button onClick={() => move(1)} aria-label="เลื่อนกราฟไปทางขวา">→</button></div>}</header>
    <div className="chart-legend">{series.map((item) => {
      const values = item.points.map((point) => point.value);
      return <span key={item.label}><i style={{ background: item.color }} />{item.label}<small>{Math.min(...values).toFixed(1)}–{Math.max(...values).toFixed(1)} {item.unit}</small></span>;
    })}</div>
    <div className="chart-scroll" ref={scroller} tabIndex={0} aria-label={`${title} เลื่อนซ้ายหรือขวาเพื่อดูข้อมูลตามเวลา`}>
      <div className="chart-canvas">
      <svg className="line-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label={title} onMouseMove={showNearest} onMouseLeave={() => setHover(null)}>
        <defs>
          {series.map((item, index) => <linearGradient key={item.label} id={`${gradientPrefix}-area-${index}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={item.color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={item.color} stopOpacity="0.03" />
          </linearGradient>)}
        </defs>
        {[0, 1, 2, 3, 4].map((line) => { const y = plot.top + line * ((chartHeight - plot.top - plot.bottom) / 4); return <line key={line} x1={plot.left} y1={y} x2={chartWidth - plot.right} y2={y} className="chart-grid-line" />; })}
        {[0, .25, .5, .75, 1].map((part) => { const timestamp = timeMin + (timeMax - timeMin) * part; const px = plot.left + part * (chartWidth - plot.left - plot.right); return <g key={part}><line x1={px} y1={plot.top} x2={px} y2={chartHeight - plot.bottom} className="chart-grid-line vertical" /><text x={px} y={chartHeight - 15} textAnchor={part === 0 ? "start" : part === 1 ? "end" : "middle"}>{new Date(timestamp).toLocaleString("th-TH", { day: period === "7 DAYS" ? "numeric" : undefined, hour: "2-digit", minute: "2-digit" })}</text></g>; })}
        {series.map((item, index) => <path className="chart-area" key={`${item.label}-area`} d={areaFor(item)} fill={`url(#${gradientPrefix}-area-${index})`} />)}
        {series.map((item) => <path key={item.label} d={pathFor(item)} fill="none" stroke={item.color} strokeWidth="3" vectorEffect="non-scaling-stroke" />)}
        {series.flatMap((item) => item.points.filter((_, index) => index % Math.max(1, Math.floor(item.points.length / 30)) === 0).map((point) => <circle key={`${item.label}-${point.timestamp_ms}`} cx={x(point.timestamp_ms)} cy={yFor(item, point.value)} r="4" fill={item.color} />))}
        {hover && <g className="chart-hover-marker" aria-hidden="true"><line x1={hover.x} y1={plot.top} x2={hover.x} y2={chartHeight - plot.bottom} />{hover.values.map((item) => <circle key={item.label} cx={hover.x} cy={item.y} r="6" fill={item.color} />)}</g>}
      </svg>
      {hover && <div className="chart-tooltip" style={{ left: Math.min(Math.max(hover.x - 105, 8), chartWidth - 218) }} role="status">
        <time>{new Date(hover.timestamp).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" })}</time>
        {hover.values.map((item) => <div key={item.label}><i style={{ background: item.color }} /><span>{item.label}</span><strong>{formatValue(item.value)} {item.unit}</strong></div>)}
      </div>}
      </div>
    </div>
  </article>;
}

export default function HistoryCharts() {
  const [history, setHistory] = useState<HistoryMap>({});
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const specs = [["vpd_kpa", 24], ["air_temp", 24], ["air_humi", 24], ["soil_temp", 24], ["soil_humi", 24], ["ph", 168]] as const;
        const responses = await Promise.all(specs.map(async ([field, hours]) => {
          const response = await fetch(`${apiBase}/api/history?field=${field}&hours=${hours}`, { cache: "no-store" });
          if (!response.ok) throw new Error("history request failed");
          return [field, (await response.json()).points ?? []] as const;
        }));
        if (!active) return;
        const next = Object.fromEntries(responses);
        setHistory(next);
        setState(Object.values(next).some((points) => points.length > 1) ? "ready" : "empty");
      } catch { if (active) setState("error"); }
    }
    load();
    const timer = window.setInterval(load, 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const charts = useMemo(() => state !== "ready" ? [] : [
    { title: "แนวโน้ม VPD", period: "24 HOURS", icon: "vpd" as const, controls: true, series: [{ label: "VPD", unit: "kPa", color: "#b9663d", points: history.vpd_kpa ?? [] }] },
    { title: "อุณหภูมิและความชื้นอากาศ", period: "24 HOURS", icon: "humidity" as const, series: [{ label: "อุณหภูมิ", unit: "°C", color: "#b9663d", points: history.air_temp ?? [] }, { label: "ความชื้น", unit: "%RH", color: "#3d7d79", points: history.air_humi ?? [] }] },
    { title: "อุณหภูมิและความชื้นดิน", period: "24 HOURS", icon: "soil-moisture" as const, series: [{ label: "อุณหภูมิดิน", unit: "°C", color: "#8b633f", points: history.soil_temp ?? [] }, { label: "ความชื้นดิน", unit: "%", color: "#6c8845", points: history.soil_humi ?? [] }] },
    { title: "แนวโน้มค่า pH ดิน", period: "7 DAYS", icon: "ph" as const, series: [{ label: "pH", unit: "pH", color: "#5876a3", points: history.ph ?? [] }] },
  ], [history, state]);

  return <section className="trends" aria-labelledby="trends-title"><div className="trends-heading"><p className="eyebrow">FIELD HISTORY</p><h2 id="trends-title">แนวโน้มเพื่อการตัดสินใจ</h2><p>ข้อมูลย้อนหลังถูกเฉลี่ยเป็นช่วงเวลาเพื่อให้เห็นภาพตลอดช่วง โดยยังคงข้อมูลต้นฉบับไว้ในฐานข้อมูล</p></div>
    {state === "loading" && <p className="trend-message" role="status">กำลังโหลดข้อมูลย้อนหลัง…</p>}
    {state === "empty" && <p className="trend-message">ยังมีข้อมูลไม่เพียงพอสำหรับแสดงกราฟ</p>}
    {state === "error" && <p className="trend-message trend-error" role="alert">โหลดข้อมูลกราฟไม่สำเร็จ กรุณาลองรีเฟรชหน้า</p>}
    {state === "ready" && <div className="trend-grid">{charts.map((chart) => <LineChart key={chart.title} {...chart} />)}</div>}
  </section>;
}
