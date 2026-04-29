import ProductCard from "./ProductCard";

/**
 * ProductGrid — responsive grid of ProductCard components.
 */
export default function ProductGrid({ results, queryType }) {
  return (
    <section className="mt-8">
      <p className="text-sm text-zinc-400 mb-4">
        <span className="font-semibold text-zinc-200">{results.length}</span> results
        {queryType === "image" ? " matching your photo" : " for your description"}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {results.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </section>
  );
}
