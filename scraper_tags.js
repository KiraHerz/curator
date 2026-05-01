// Tag + cover + published_at + awards scraper
// Run on any Behance page while logged in

const API = 'https://curator-1-1uy9.onrender.com';
const BAD_TAGS = new Set(['id','title','url','name','type','slug','null','undefined','true','false','project','design','behance']);

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function guessCategory(title, tags) {
  const text = (title + ' ' + tags.join(' ')).toLowerCase();
  if (/mobile|ios|android|app|iphone/.test(text)) return 'mobile';
  if (/brand|identity|logo|branding|rebrand/.test(text)) return 'branding';
  if (/poster|print|editorial|typography/.test(text)) return 'poster';
  if (/ux|ui|interface|dashboard|saas|wireframe/.test(text)) return 'ux-ui';
  return null;
}

function detectAwards(html) {
  if (/adobe.*award|award.*adobe/i.test(html)) return 'adobe_award';
  if (/"is_featured"\s*:\s*true|"featured"\s*:\s*true/i.test(html)) return 'featured';
  if (/"appreciated_by_fields"|"appreciation_count"\s*:\s*([5-9]\d{3}|\d{5,})/i.test(html)) return 'appreciated';
  return null;
}

const all = await (await fetch(`${API}/projects/?limit=2000`)).json();
const toProcess = all.filter(p => {
  const tags = (p.tags || []).map(t => t.name || t);
  const hasBadTags = tags.some(t => BAD_TAGS.has(t.toLowerCase()));
  const hasNoTags = tags.length === 0;
  const noAwardsChecked = !p.awards;
  return hasNoTags || hasBadTags || noAwardsChecked;
});

console.log(`Total: ${all.length}, to process: ${toProcess.length}`);

let updated = 0;
for (let i = 0; i < toProcess.length; i++) {
  const p = toProcess[i];
  try {
    const r = await fetch(p.url, { credentials: 'include' });
    const html = await r.text();

    const tags = [...new Set([
      ...[...html.matchAll(/"tag":"([^"]{2,40})"/g)].map(m => m[1].toLowerCase()),
      ...[...html.matchAll(/"tags":\[([^\]]+)\]/g)]
        .flatMap(m => [...m[1].matchAll(/"([^"]{2,40})"/g)].map(x => x[1].toLowerCase()))
    ])].filter(t => !BAD_TAGS.has(t) && !/^\d+$/.test(t) && t.length > 1).slice(0, 8);

    const coverMatch = html.match(/(https:\/\/mir-s3-cdn-cf\.behance\.net\/projects\/[^\s"']+\.(?:jpg|jpeg|png|webp))/i);
    const cover = coverMatch ? coverMatch[1] : null;

    const pubMatch = html.match(/"publishedOn":(\d{9,10})/) || html.match(/"published_on":(\d{9,10})/);
    const published_at = pubMatch ? new Date(parseInt(pubMatch[1]) * 1000).toISOString() : null;

    const awards = detectAwards(html);
    const cat = guessCategory(p.title, tags);

    const body = {};
    if (tags.length) body.tags = tags;
    if (cover && !p.cover_url) body.cover_url = cover;
    if (published_at) body.published_at = published_at;
    if (awards) body.awards = awards;
    if (cat) body.category = cat;

    if (Object.keys(body).length) {
      await fetch(`${API}/projects/${p.id}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
      });
      updated++;
    }
  } catch(e) {}

  if ((i + 1) % 50 === 0) console.log(`Progress: ${i+1}/${toProcess.length} — updated: ${updated}`);
  await sleep(600);
}

await fetch(`${API}/score/recalculate`, { method: 'POST' });
console.log(`Done! Updated: ${updated}`);
