import { useRef, useState } from "react";

/**
 * ImageUpload — drag-and-drop zone for fashion photo uploads.
 * Props:
 *   onFile(file: File) — called when user drops or selects an image
 */
export default function ImageUpload({ onFile, disabled }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);

  function handleFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    setPreview(URL.createObjectURL(file));
    onFile(file);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`
        relative flex flex-col items-center justify-center gap-3
        rounded-2xl border-2 border-dashed
        cursor-pointer transition-all duration-200
        h-48 overflow-hidden
        ${dragging
          ? "border-brand-400 bg-brand-500/10 scale-[1.01]"
          : "border-white/20 bg-white/3 hover:border-brand-500/50 hover:bg-white/5"
        }
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      {preview ? (
        <>
          <img src={preview} alt="preview" className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
            <span className="text-sm font-medium text-white/80">Click to change</span>
          </div>
        </>
      ) : (
        <>
          <div className="w-12 h-12 rounded-full bg-brand-500/10 flex items-center justify-center">
            <svg className="w-6 h-6 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-zinc-300">Drop a fashion photo here</p>
            <p className="text-xs text-zinc-500 mt-0.5">JPG, PNG or WebP — max 5 MB</p>
          </div>
        </>
      )}
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp"
        className="hidden" onChange={(e) => handleFile(e.target.files[0])} />
    </div>
  );
}
