import { Home, Search, Heart, User } from 'lucide-react';
import { NavLink } from 'react-router-dom';

export default function BottomNav() {
  const navItems = [
    { icon: Home, label: 'Home', path: '/' },
    { icon: Search, label: 'Search', path: '/results' },
    { icon: Heart, label: 'Saved', path: '/saved' },
    { icon: User, label: 'Profile', path: '/onboarding' },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-md border-t border-cream-300 pb-safe z-50">
      <div className="flex justify-around items-center h-16 px-6 max-w-md mx-auto">
        {navItems.map(({ icon: Icon, label, path }) => (
          <NavLink 
            key={label}
            to={path}
            className={({ isActive }) => 
              `flex flex-col items-center gap-1 transition-colors duration-200 ${
                isActive ? 'text-dustyrose-500' : 'text-charcoal-800/50 hover:text-charcoal-900'
              }`
            }
          >
            <Icon size={24} strokeWidth={2} className="mb-0.5" />
            <span className="text-[10px] font-medium tracking-wide">{label}</span>
          </NavLink>
        ))}
      </div>
    </div>
  );
}
