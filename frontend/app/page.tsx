"use client";

import { useEffect, useState } from "react";
import WeatherForecast from "./WeatherForecast";
import HistoryCharts from "./HistoryCharts";
import SensorIcon from "./SensorIcon";

type Reading = Record<string, number | string | null | undefined>;

const metrics = [
  ["air_temp", "อุณหภูมิอากาศ", "°C", "CANOPY", "temperature"],
  ["air_humi", "ความชื้นอากาศ", "%RH", "CANOPY", "humidity"],
  ["vpd_kpa", "ค่า VPD", "kPa", "CANOPY", "vpd"],
  ["soil_temp", "อุณหภูมิดิน", "°C", "ROOT ZONE", "soil-temperature"],
  ["soil_humi", "ความชื้นดิน", "%", "ROOT ZONE", "soil-moisture"],
  ["ph", "ค่า pH ดิน", "pH", "ROOT ZONE", "ph"],
] as const;

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";

function number(value: Reading[string], digits = 1) {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

export default function Home() {
  const [reading, setReading] = useState<Reading>({});
  const [connection, setConnection] = useState("กำลังเชื่อมต่อข้อมูลแปลง");

  useEffect(() => {
    let socket: WebSocket | undefined;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const response = await fetch(`${apiBase}/api/latest`, { cache: "no-store" });
        if (!response.ok) throw new Error("Latest request failed");
        const payload = await response.json();
        setReading(payload.data ?? {});
        setConnection("ข้อมูลแปลงออนไลน์");
      } catch {
        setConnection("กำลังรอข้อมูลจากสถานี");
      }
    };
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const host = apiBase ? new URL(apiBase).host : window.location.host;
      socket = new WebSocket(`${protocol}://${host}/ws`);
      socket.onopen = load;
      socket.onmessage = (event) => {
        setReading(JSON.parse(event.data).data ?? {});
        setConnection("ข้อมูลแปลงออนไลน์");
      };
      socket.onclose = () => { retry = setTimeout(connect, 3000); };
    };
    load();
    connect();
    return () => { socket?.close(); if (retry) clearTimeout(retry); };
  }, []);

  const updated = typeof reading.timestamp_ms === "number"
    ? new Intl.DateTimeFormat("th-TH", { dateStyle: "medium", timeStyle: "short" }).format(reading.timestamp_ms)
    : "ยังไม่มีข้อมูล";

  return (
    <main>
      <nav className="nav" aria-label="เมนูหลัก">
        <a className="brand" href="#top"><span>พ</span><strong>สวนพรรณมณี</strong></a>
        <a className="nav-link" href="#dashboard">ดูข้อมูลแปลง</a>
      </nav>
      <section className="hero" id="top">
        <p className="eyebrow">DURIAN FIELD STATION · 01</p>
        <h1>ดูแลสวนจาก<br /><em>ข้อมูลจริง</em> ทุกวัน</h1>
        <p className="lead">สถานีตรวจวัดสภาพอากาศและดิน ช่วยให้การดูแลทุเรียนเริ่มจากสภาพแปลงปัจจุบัน ไม่ใช่การคาดเดา</p>
        <a className="primary-link" href="#dashboard">เข้าสู่ข้อมูลแปลง <span aria-hidden="true">↓</span></a>
        <div className="field-line" aria-hidden="true"><i /><i /><i /><i /><i /></div>
      </section>
      <section className="dashboard" id="dashboard" aria-labelledby="dashboard-title">
        <div className="section-head">
          <div><p className="eyebrow">LIVE ORCHARD CONDITION</p><h2 id="dashboard-title">สภาพแปลงล่าสุด</h2></div>
          <div className="live-status"><span className="pulse" />{connection}<small>อัปเดต {updated}</small></div>
        </div>
        <div className="metric-grid">
          {metrics.map(([key, label, unit, group, icon]) => <article className="metric" key={key}>
            <div className="metric-top"><p>{group}</p><SensorIcon type={icon} /></div><h3>{label}</h3><strong>{number(reading[key], key === "vpd_kpa" || key === "ph" ? 2 : 1)}<small>{unit}</small></strong>
          </article>)}
        </div>
        <div className="advice-grid">
          <article><p className="eyebrow">CANOPY DECISION</p><h3>คำแนะนำจาก VPD</h3><strong>{String(reading.vpd_status ?? "กำลังรอข้อมูล")}</strong><p>{String(reading.vpd_message ?? "ระบบจะแสดงคำแนะนำเมื่อสถานีส่งข้อมูลเข้ามา")}</p></article>
          <article><p className="eyebrow">ROOT ZONE DECISION</p><h3>คำแนะนำจาก pH</h3><strong>{String(reading.ph_status ?? "กำลังรอข้อมูล")}</strong><p>{String(reading.ph_message ?? "ระบบจะแสดงคำแนะนำเมื่อสถานีส่งข้อมูลเข้ามา")}</p></article>
        </div>
      </section>
      <HistoryCharts />
      <WeatherForecast />
      <footer>
        <div className="footer-organization">
          <strong>คณะวิทยาศาสตร์และเทคโนโลยี มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี</strong>
          <span>สาขาวิชาการวิเคราะห์และจัดการข้อมูลขนาดใหญ่</span>
        </div>
        <small>สวนพรรณมณี · ระบบติดตามสภาพแปลงทุเรียนแบบเรียลไทม์</small>
      </footer>
    </main>
  );
}
