const sections = [...document.querySelectorAll('main section[id]')];
const links = [...document.querySelectorAll('nav a[href^="#"]')];
let queued = false;
function updateChapter() {
  queued = false;
  let active = null;
  for (const section of sections) if (section.getBoundingClientRect().top <= 150) active = section.id;
  for (const link of links) {
    if (link.hash === '#' + active) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
}
document.addEventListener('scroll', () => {
  if (!queued) { queued = true; requestAnimationFrame(updateChapter); }
}, {passive:true});
document.querySelectorAll('.mobile-contents a').forEach(link => link.addEventListener('click', () => {
  document.querySelector('.mobile-contents').open = false;
}));
updateChapter();

function revealHash() {
  let id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
  const target = document.getElementById(id);
  if (!target) return;
  for (let parent = target.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === 'DETAILS') parent.open = true;
  }
  target.scrollIntoView({block:'start'});
}
window.addEventListener('hashchange', revealHash);
if (location.hash) revealHash();
for (const link of document.querySelectorAll('[data-reader-back]')) {
  try {
    const prior = new URL(document.referrer);
    const current = new URL(location.href);
    if (['https:','http:'].includes(prior.protocol) && prior.origin + prior.pathname + prior.search !== current.origin + current.pathname + current.search) link.href = prior.href;
  } catch (_) { /* Direct visits retain the ordinary home link. */ }
}
