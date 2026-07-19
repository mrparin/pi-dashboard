"use client";

import { useEffect, useState } from "react";

type Location = { name: string; admin1?: string; lat: number; lon: number };
type Daily = {
  time: string[];
  weathercode: number[];
  condition_text?: string[];
  temperature_2m_max: Array<number | null>;
  temperature_2m_min: Array<number | null>;
  precipitation_sum: Array<number | null>;
  precipitation_probability_max: Array<number | null>;
  windspeed_10m_max: Array<number | null>;
};
type Forecast = { source_label?: string; daily: Daily };
type SubDistrict = { id: number; name: string; lat: number | null; lon: number | null };
type District = { id: number; name: string; sub_districts: SubDistrict[] };
type Province = { id: number; name: string; districts: District[] };

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";
const locationKey = "weather_location";
const descriptions: Record<number, string> = {
  0: "ท้องฟ้าแจ่มใส", 1: "ท้องฟ้าโปร่ง", 2: "มีเมฆบางส่วน", 3: "มีเมฆมาก",
  45: "มีหมอก", 48: "หมอกจัด", 51: "ฝนปรอยเบา", 53: "ฝนปรอย", 55: "ฝนปรอยหนัก",
  61: "ฝนเบา", 63: "ฝนปานกลาง", 65: "ฝนหนัก", 80: "ฝนเล็กน้อย", 81: "ฝนหนัก",
  82: "ฝนหนักมาก", 95: "พายุฝนฟ้าคะนอง", 96: "พายุลูกเห็บ", 99: "พายุลูกเห็บหนัก",
};

function weatherIcon(code: number) {
  if (code === 0 || code === 1) return "☀";
  if (code === 2 || code === 3) return "☁";
  if (code === 45 || code === 48) return "≋";
  if (code >= 95) return "ϟ";
  return "☂";
}

export default function WeatherForecast() {
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [provinceId, setProvinceId] = useState("");
  const [districtId, setDistrictId] = useState("");
  const [subDistrictId, setSubDistrictId] = useState("");
  const [location, setLocation] = useState<Location | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [state, setState] = useState<"idle" | "locations" | "loading" | "ready" | "error">("locations");

  const selectedProvince = provinces.find((province) => String(province.id) === provinceId);
  const districts = selectedProvince?.districts ?? [];
  const selectedDistrict = districts.find((district) => String(district.id) === districtId);
  const subDistricts = selectedDistrict?.sub_districts ?? [];

  async function loadWeather(selected: Location) {
    setLocation(selected);
    setState("loading");
    localStorage.setItem(locationKey, JSON.stringify(selected));
    try {
      const response = await fetch(`${apiBase}/api/weather?lat=${selected.lat}&lon=${selected.lon}`);
      if (!response.ok) throw new Error("weather request failed");
      setForecast(await response.json());
      setState("ready");
    } catch {
      setForecast(null);
      setState("error");
    }
  }

  useEffect(() => {
    async function loadLocations() {
      try {
        const response = await fetch(`${apiBase}/api/thai-locations`);
        if (!response.ok) throw new Error("location request failed");
        const payload = await response.json();
        setProvinces(payload.provinces ?? []);
        setState((current) => current === "locations" ? "idle" : current);
      } catch {
        setState("error");
      }
    }
    loadLocations();
    const saved = localStorage.getItem(locationKey);
    if (!saved) return;
    try { loadWeather(JSON.parse(saved)); } catch { localStorage.removeItem(locationKey); }
  }, []);

  function selectProvince(value: string) {
    setProvinceId(value);
    setDistrictId("");
    setSubDistrictId("");
  }

  function selectDistrict(value: string) {
    setDistrictId(value);
    setSubDistrictId("");
  }

  async function selectSubDistrict(value: string) {
    setSubDistrictId(value);
    const selected = subDistricts.find((subDistrict) => String(subDistrict.id) === value);
    if (!selected || !selectedProvince || !selectedDistrict) return;

    let lat = selected.lat;
    let lon = selected.lon;
    if (lat == null || lon == null) {
      setState("loading");
      try {
        const terms = `${selected.name} ${selectedDistrict.name} ${selectedProvince.name}`;
        const response = await fetch(`${apiBase}/api/geocode?q=${encodeURIComponent(terms)}`);
        if (!response.ok) throw new Error("geocode request failed");
        const result = (await response.json()).results?.[0];
        if (!result?.lat || !result?.lon) throw new Error("coordinates unavailable");
        lat = result.lat;
        lon = result.lon;
      } catch {
        setState("error");
        return;
      }
    }

    loadWeather({ name: selected.name, admin1: `${selectedDistrict.name} · ${selectedProvince.name}`, lat: Number(lat), lon: Number(lon) });
  }

  return <section className="weather" id="weather" aria-labelledby="weather-title">
    <div className="weather-heading">
      <div><p className="eyebrow">FIELD OUTLOOK · 7 DAYS</p><h2 id="weather-title">พยากรณ์ก่อนลงมือ</h2></div>
      <div className="weather-location">
        <strong>{location ? `${location.name}${location.admin1 ? ` · ${location.admin1}` : ""}` : "เลือกพื้นที่พยากรณ์"}</strong>
        {forecast?.source_label && <small>แหล่งข้อมูล {forecast.source_label}</small>}
      </div>
    </div>
    <div className="location-cascade" aria-label="เลือกพื้นที่พยากรณ์อากาศ">
      <label><span>1 · จังหวัด</span><select value={provinceId} onChange={(event) => selectProvince(event.target.value)} disabled={state === "locations"}><option value="">{state === "locations" ? "กำลังโหลดรายการ…" : "เลือกจังหวัด"}</option>{provinces.map((province) => <option value={province.id} key={province.id}>{province.name}</option>)}</select></label>
      <label><span>2 · อำเภอ / เขต</span><select value={districtId} onChange={(event) => selectDistrict(event.target.value)} disabled={!provinceId}><option value="">เลือกอำเภอ</option>{districts.map((district) => <option value={district.id} key={district.id}>{district.name}</option>)}</select></label>
      <label><span>3 · ตำบล / แขวง</span><select value={subDistrictId} onChange={(event) => selectSubDistrict(event.target.value)} disabled={!districtId}><option value="">เลือกตำบล</option>{subDistricts.map((subDistrict) => <option value={subDistrict.id} key={subDistrict.id}>{subDistrict.name}</option>)}</select></label>
    </div>
    {state === "loading" && <p className="weather-message" role="status">กำลังโหลดพยากรณ์อากาศ 7 วัน…</p>}
    {state === "error" && <p className="weather-message weather-error" role="alert">โหลดข้อมูลไม่สำเร็จ กรุณาลองค้นหาพื้นที่อีกครั้ง</p>}
    {(state === "idle" || state === "locations") && !forecast && <p className="weather-message">เลือกจังหวัด อำเภอ และตำบลตามลำดับเพื่อดูพยากรณ์อากาศล่วงหน้า</p>}
    {state === "ready" && forecast?.daily && <div className="forecast-grid">
      {forecast.daily.time.map((date, index) => {
        const code = forecast.daily.weathercode[index];
        const rainChance = forecast.daily.precipitation_probability_max[index];
        const rain = forecast.daily.precipitation_sum[index];
        const wind = forecast.daily.windspeed_10m_max[index];
        return <article className="forecast-day" key={date}>
          <p className="forecast-date">{index === 0 ? "วันนี้" : new Date(`${date}T00:00:00`).toLocaleDateString("th-TH", { weekday: "short" })}<small>{new Date(`${date}T00:00:00`).toLocaleDateString("th-TH", { day: "numeric", month: "short" })}</small></p>
          <span className="forecast-icon" aria-hidden="true">{weatherIcon(code)}</span>
          <p className="forecast-desc">{forecast.daily.condition_text?.[index] || descriptions[code] || "ไม่ทราบสภาพอากาศ"}</p>
          <p className="forecast-temp"><strong>{forecast.daily.temperature_2m_max[index] ?? "—"}°</strong><span>/ {forecast.daily.temperature_2m_min[index] ?? "—"}°</span></p>
          <dl><div><dt>โอกาสเกิดฝน</dt><dd>{rainChance == null ? "ไม่มีข้อมูล" : `${Math.round(rainChance)}%`}</dd></div><div><dt>ปริมาณฝน</dt><dd>{rain == null ? "—" : `${Number(rain).toFixed(1)} มม.`}</dd></div><div><dt>ลมสูงสุด</dt><dd>{wind == null ? "—" : `${Number(wind).toFixed(1)} กม./ชม.`}</dd></div></dl>
        </article>;
      })}
    </div>}
  </section>;
}
