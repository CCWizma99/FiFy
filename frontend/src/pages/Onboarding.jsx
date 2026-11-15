import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Onboarding() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState('Minimalist');

  const vibes = [
    { name: 'Minimalist', img: '/product-fallback.svg' },
    { name: 'Streetwear', img: '/product-fallback.svg' },
    { name: 'Dark Academia', img: '/product-fallback.svg' },
    { name: 'Coastal', img: '/product-fallback.svg' },
  ];

  return (
    <div className="min-h-screen bg-cream-100 flex flex-col items-center justify-center px-6 py-12 animate-fade-in max-w-md mx-auto">
      <h1 className="text-4xl font-serif text-charcoal-900 tracking-tight mb-2">Fify</h1>
      <p className="text-charcoal-800/60 text-sm font-medium mb-12 italic">Seen it? Find it.</p>

      <h2 className="text-2xl font-serif text-charcoal-900 mb-8 self-start">What's your vibe?</h2>

      <p className="mb-4">Selected style: {selected}</p>
      <div className="grid grid-cols-2 gap-4 w-full mb-12">
        {vibes.map(vibe => (
          <button aria-label={vibe.name} onClick={() => setSelected(vibe.name)} aria-pressed={selected === vibe.name} key={vibe.name} className="relative aspect-square rounded-2xl overflow-hidden group cursor-pointer border-2 border-transparent hover:border-dustyrose-400 transition-all shadow-sm">
            <img src={vibe.img} alt={vibe.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
            <div className="absolute inset-0 bg-gradient-to-t from-charcoal-900/80 via-charcoal-900/20 to-transparent flex flex-col justify-end p-4">
              <span className="text-white font-medium text-sm drop-shadow-md">{vibe.name}</span>
            </div>
          </button>
        ))}
      </div>

      <button onClick={() => navigate('/results', { state: { type: 'text', query: selected } })} className="btn-primary w-full max-w-xs shadow-dustyrose-500/25 py-4 text-base">
        Start Finding
      </button>
    </div>
  );
}
