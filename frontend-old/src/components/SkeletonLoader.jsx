/**
 * SkeletonLoader — displays an animated skeleton grid while results load.
 */
export default function SkeletonLoader({ count = 8 }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-8 animate-fade-in">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass rounded-2xl overflow-hidden">
          <div className="aspect-[3/4] bg-white/5 animate-pulse-slow" />
          <div className="p-4 space-y-2">
            <div className="h-3 bg-white/5 rounded animate-pulse-slow w-3/4" />
            <div className="h-3 bg-white/5 rounded animate-pulse-slow w-1/2" />
            <div className="h-4 bg-white/5 rounded animate-pulse-slow w-1/3 mt-3" />
          </div>
        </div>
      ))}
    </div>
  );
}
