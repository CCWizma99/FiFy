import { useNavigate } from 'react-router-dom';

export default function Onboarding() {
  const navigate = useNavigate();

  const vibes = [
    { name: 'Minimalist', img: 'https://images.unsplash.com/photo-1434389678369-184bf3585206?auto=format&fit=crop&w=300&q=80' },
    { name: 'Streetwear', img: 'https://images.unsplash.com/photo-1523398002811-999aa8d9512e?auto=format&fit=crop&w=300&q=80' },
    { name: 'Dark Academia', img: 'https://images.unsplash.com/photo-1485230405346-71acb9518d9c?auto=format&fit=crop&w=300&q=80' },
    { name: 'Coastal', img: 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=300&q=80' },
  ];

  return (
    <div className="min-h-screen bg-cream-100 flex flex-col items-center justify-center px-6 py-12 animate-fade-in max-w-md mx-auto">
      <h1 className="text-4xl font-serif text-charcoal-900 tracking-tight mb-2">Fify</h1>
      <p className="text-charcoal-800/60 text-sm font-medium mb-12 italic">Seen it? Find it.</p>

      <h2 className="text-2xl font-serif text-charcoal-900 mb-8 self-start">What's your vibe?</h2>

      <div className="grid grid-cols-2 gap-4 w-full mb-12">
        {vibes.map(vibe => (
          <div key={vibe.name} className="relative aspect-square rounded-2xl overflow-hidden group cursor-pointer border-2 border-transparent hover:border-dustyrose-400 transition-all shadow-sm">
            <img src={vibe.img} alt={vibe.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
            <div className="absolute inset-0 bg-gradient-to-t from-charcoal-900/80 via-charcoal-900/20 to-transparent flex flex-col justify-end p-4">
              <span className="text-white font-medium text-sm drop-shadow-md">{vibe.name}</span>
            </div>
          </div>
        ))}
      </div>

      <button onClick={() => navigate('/')} className="btn-primary w-full max-w-xs shadow-dustyrose-500/25 py-4 text-base">
        Start Finding
      </button>
    </div>
  );
}
