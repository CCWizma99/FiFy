import { useState } from "react";

/**
 * SearchBar — text description input + search button.
 * Props:
 *   onSearch(query: string) — called on submit
 *   disabled: bool
 */
export default function SearchBar({ onSearch, disabled }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const q = value.trim();
    if (q) onSearch(q);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        id="text-search-input"
        type="text"
        className="input-base flex-1"
        placeholder="Describe what you're looking for... e.g. 'red floral summer dress'"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        maxLength={200}
      />
      <button
        id="text-search-btn"
        type="submit"
        className="btn-primary px-5 shrink-0"
        disabled={disabled || !value.trim()}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        Search
      </button>
    </form>
  );
}
