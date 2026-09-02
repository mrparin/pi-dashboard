export type SensorIconType = "temperature" | "humidity" | "vpd" | "soil-temperature" | "soil-moisture" | "ph" | "eto";

export default function SensorIcon({ type }: { type: SensorIconType }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return <span className="sensor-icon" aria-hidden="true"><svg viewBox="0 0 24 24" {...common}>
    {(type === "temperature" || type === "soil-temperature") && <><path d="M9 4a3 3 0 0 1 6 0v9.2a5 5 0 1 1-6 0Z" /><path d="M12 7v9" /><circle cx="12" cy="17" r="1.5" />{type === "soil-temperature" && <path d="M3 21h18M5 18.5l2 2.5m12-2.5-2 2.5" />}</>}
    {(type === "humidity" || type === "soil-moisture") && <><path d="M12 2.5s6 6.7 6 12a6 6 0 0 1-12 0c0-5.3 6-12 6-12Z" /><path d="M9 16.5c.8 1.2 1.8 1.7 3 1.7" />{type === "soil-moisture" && <path d="M4 21h16M6 19.5h12" />}</>}
    {type === "vpd" && <><path d="M4 14c5.2.4 8.5-2.1 10-8 3.6 2.5 5.6 6 4.7 9.2C17.7 19 13.8 21 9.8 19.8" /><path d="M5 20c3.2-4.5 6.7-7.6 10.5-9.3M4 8v3m-1.5-1.5h3" /></>}
    {type === "ph" && <><path d="M8 3v5l-4 8.5A3 3 0 0 0 6.7 21h10.6a3 3 0 0 0 2.7-4.5L16 8V3M7 13h10M9 3h6" /><text x="8.2" y="18.2" fill="currentColor" stroke="none" fontSize="5.5" fontWeight="700">pH</text></>}
    {type === "eto" && <><circle cx="17" cy="7" r="3" /><path d="M17 2v1M17 11v1M12 7h1M21 7h1M12 14c0 3-2.3 5.5-5 5.5S2 17 2 14c0-3.2 5-8 5-8s5 4.8 5 8Z" /><path d="M5 15.2c.5.8 1.1 1.1 2 1.1" /></>}
  </svg></span>;
}
