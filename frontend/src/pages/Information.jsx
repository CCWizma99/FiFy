const content = {
  about: ['About FiFy', 'FiFy helps you discover fashion products using text and image searches. Results depend on the available catalog.'],
  privacy: ['Privacy', 'Favorites stay in your browser storage. Search text and uploaded images are sent to the configured FiFy backend for processing. Retailer links open third-party sites with their own privacy policies.'],
  terms: ['Terms', 'Catalog prices and availability may change. Verify details with the retailer before purchasing. FiFy does not sell these products or guarantee a match.'],
  contact: ['Contact', 'Report a problem or suggest an improvement through our GitHub issue tracker.'],
};
export default function Information({ page }) {
  const [title, text] = content[page];
  return <main className="p-8 max-w-3xl"><h1 className="text-3xl mb-4">{title}</h1><p>{text}</p>
    {page === 'contact' && <a href="https://github.com/CCWizma99/FiFy/issues">Open FiFy issues</a>}</main>;
}
