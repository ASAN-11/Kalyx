import { useState, type ReactNode } from "react";
/** Looks for /assets/<name>.mp4 then /assets/<name>.jpg; falls back to a gradient. */
export default function MediaHolder({ name, tone = "earth", className = "", children }: { name: string; tone?: string; className?: string; children?: ReactNode }) {
  const [video, setVideo] = useState(true);
  const [img, setImg] = useState(true);
  return (
    <div className={`holder ${tone} ${className}`}>
      {img && <img className="bg" src={`/assets/${name}.png`} alt="" onError={() => setImg(false)} />}
      {video && <video className="bg" src={`/assets/${name}.mp4`} autoPlay muted loop playsInline onError={() => setVideo(false)} />}
      <div className="shade" />
      {children}
    </div>
  );
}
