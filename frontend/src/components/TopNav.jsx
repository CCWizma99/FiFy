import { Link } from 'react-router-dom';

export default function TopNav() {
  return (
    <nav className="bg-navy px-5 md:px-12 h-[62px] flex items-center justify-between sticky top-0 z-[100]">
      <Link to="/" className="font-serif text-[28px] font-semibold text-white tracking-tight -ml-1 no-underline">
        fi<span className="text-[#D4AF37]">f</span>y
      </Link>

      <div className="flex items-center gap-5">
        <Link to="/admin" className="hidden md:block text-[12.5px] text-white/65 hover:text-white transition-colors no-underline font-sans">Admin</Link>
        <Link to="/onboarding" className="hidden md:block text-[12.5px] text-white/65 hover:text-white transition-colors no-underline font-sans">Inspirations</Link>
        <Link to="/saved" className="px-[18px] py-[7px] border border-white/30 rounded-[20px] bg-transparent text-[12.5px] text-white/85 hover:bg-white/10 transition-colors cursor-pointer font-sans">
          Saved items
        </Link>
        <div className="hidden md:block bg-[#D4AF37] text-navy text-[10px] font-medium px-2.5 py-1 rounded-xl">New</div>
      </div>
    </nav>
  );
}
