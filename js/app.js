/* global APP_CONFIG */
(function(){
  const dataUrl = (window.APP_CONFIG && window.APP_CONFIG.dataUrl) || 'schema.json';
  const speciesSelect = document.getElementById('species-select');
  const variableSelect = document.getElementById('variable-select');
  const resultsEl = document.getElementById('results');
  const statusEl = document.getElementById('status');
  const lastUpdatedEl = document.getElementById('last-updated');

  let rawData = null;
  let speciesList = [];
  // Map variable key (slug) -> human-readable label (long form)
  let variableMap = new Map();

  function slugVariable(fileName, label){
    // Prefer pattern speciescode_xxx.png -> remove first token (species code) and extension
    if(!fileName) return label ? label.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') : '';
    const noExt = fileName.replace(/\.png$/i,'');
    const parts = noExt.split('_');
    if(parts.length > 1) parts.shift();
    const core = parts.join('_');
    return core.toLowerCase();
  }

  function parseData(json){
    speciesList = json.species.slice().sort((a,b)=>a.species_name.localeCompare(b.species_name));
    speciesList.forEach(sp => {
      sp.images.forEach(img => {
        const key = slugVariable(img.file_name, img.label);
        if(!variableMap.has(key)){
          variableMap.set(key, img.label || key);
        }
      });
    });
  }

  function populateControls(){
    const entries = Array.from(variableMap.entries())
      .sort((a,b)=> a[1].localeCompare(b[1])); // sort by label
    variableSelect.innerHTML = '<option value="">Select variable...</option>' + entries.map(([key,label])=>`<option value="${key}">${label}</option>`).join('');
  }

  function getSpeciesByCode(code){
    return speciesList.find(sp => sp.species_code.toLowerCase() === code.toLowerCase());
  }

  function filterState(){
    const speciesCode = speciesSelect.value.trim();
    const variableKey = variableSelect.value.trim();
    // Auto-derive mode: variable overrides species if both present (though we clear one when setting the other)
    const mode = variableKey ? 'variable' : (speciesCode ? 'species' : null);
    return { speciesCode, variableKey, mode };
  }

  function applyPermalink(){
    const params = new URLSearchParams(location.search);
    const sp = params.get('species');
    const v = params.get('variable');
    if(v){
      variableSelect.value = v;
    } else if(sp){
      const match = speciesList.find(s=>s.species_code.toLowerCase()===sp.toLowerCase());
      if(match){ speciesSelect.value = match.species_code; }
    }
  }

  function updatePermalink(state){
    const params = new URLSearchParams();
    if(state.mode==='species' && state.speciesCode){
      const match = getSpeciesByCode(state.speciesCode);
      if(match) params.set('species', match.species_code);
    } else if(state.mode==='variable' && state.variableKey){
      params.set('variable', state.variableKey);
    }
    const newUrl = params.toString() ? '?' + params.toString() : location.pathname;
    history.replaceState(null,'', newUrl);
  }

  function render(){
    const state = filterState();
    updatePermalink(state);
    resultsEl.innerHTML = '';

    function buildImageBlock(sp, img){
      const block = document.createElement('div');
      block.className='image-block';
      const imageEl = document.createElement('img');
      imageEl.loading = 'lazy';
      imageEl.src = img.url;
      imageEl.alt = `${sp.species_name} — ${img.label}`;
      imageEl.addEventListener('error', ()=> {
        block.classList.add('load-error');
        block.innerHTML = `<div class="image-error">Failed to load image.<br><a href="${img.url}" target="_blank" rel="noopener">Open directly</a></div>`;
      }, { once:true });
      // Maximize on click
      imageEl.style.cursor = 'zoom-in';
      imageEl.addEventListener('click', () => {
        showImageOverlay(img.url, imageEl.alt);
      });
      const meta = document.createElement('div');
      meta.className = 'image-meta';
      meta.innerHTML = `<a href="${img.url}" download title="Download PNG">PNG</a>`;
      block.appendChild(imageEl);
      block.appendChild(meta);
      return block;
    }

    // Overlay logic for maximizing images
    function showImageOverlay(url, alt) {
      // Prevent multiple overlays
      if(document.getElementById('image-overlay')) return;
      const overlay = document.createElement('div');
      overlay.id = 'image-overlay';
      overlay.className = 'image-overlay';
      overlay.innerHTML = `
        <button class="overlay-close" title="Close">×</button>
        <img src="${url}" alt="${alt}" class="overlay-img" />
      `;
      document.body.appendChild(overlay);
      // Focus close button for accessibility
      const closeBtn = overlay.querySelector('.overlay-close');
      closeBtn.focus();
      closeBtn.addEventListener('click', () => {
        overlay.remove();
      });
      // Also close on overlay click (but not image click)
      overlay.addEventListener('click', (e) => {
        if(e.target === overlay) overlay.remove();
      });
      // ESC key closes overlay
      function escListener(e) {
        if(e.key === 'Escape') {
          overlay.remove();
          document.removeEventListener('keydown', escListener);
        }
      }
      document.addEventListener('keydown', escListener);
    }

    if(state.mode === 'species'){
      if(!state.speciesCode){
        statusEl.textContent = 'Select a species to view its maps.';
        return; }
      const sp = getSpeciesByCode(state.speciesCode);
      if(!sp){ statusEl.textContent = 'No species matched.'; return; }
      statusEl.textContent = '';
      const card = document.createElement('div');
      card.className = 'species-card';
      const imagesWrap = document.createElement('div');
      imagesWrap.className = 'images-grid';
      sp.images.forEach(img => imagesWrap.appendChild(buildImageBlock(sp,img)));
      card.appendChild(imagesWrap);
      resultsEl.appendChild(card);
    } else if(state.mode === 'variable') {
      if(!state.variableKey){ statusEl.textContent = 'Select a variable to view across species.'; return; }
      statusEl.textContent = '';
      // For each species, find image whose slugVariable matches selected key
      const matches = [];
      speciesList.forEach(sp => {
        const img = sp.images.find(im => slugVariable(im.file_name, im.label) === state.variableKey);
        if(img){ matches.push({ sp, img }); }
      });
      if(!matches.length){ resultsEl.innerHTML = '<div class="empty">No images for this variable.</div>'; return; }
      matches.forEach(({sp,img}) => {
        const div = document.createElement('div');
        div.className='variable-card';
        // Reuse shared image block; no species heading per request
        div.appendChild(buildImageBlock(sp,img));
        resultsEl.appendChild(div);
      });
    } else {
      statusEl.textContent = 'Select a species or variable to begin.';
    }
  }

  function attachEvents(){
  speciesSelect.addEventListener('change', ()=> { if(speciesSelect.value){ variableSelect.value=''; } render(); });
  variableSelect.addEventListener('change', ()=> { if(variableSelect.value){ speciesSelect.value=''; } render(); });
  }

  function setLastUpdated(){
    try {
      const now = new Date();
      lastUpdatedEl.textContent = now.toISOString().split('T')[0];
    } catch(e){ /* no-op */ }
  }

  async function init(){
    statusEl.textContent = 'Loading data...';
    try {
      const resp = await fetch(dataUrl, { cache: 'no-cache' });
      if(!resp.ok) throw new Error('Fetch failed: '+resp.status);
      const json = await resp.json();
      rawData = json;
      parseData(json);
      populateControls();
      // Populate species dropdown
      const speciesOptions = ['<option value="">Select species...</option>'].concat(
        speciesList.map(sp => `<option value="${sp.species_code}">${sp.species_name}</option>`)
      );
      speciesSelect.innerHTML = speciesOptions.join('');
      applyPermalink();
      attachEvents();
      setLastUpdated();
      render();
    } catch(err){
  console.error('Failed to load data file', dataUrl, err);
  const isFileProto = location.protocol === 'file:';
  const hint = isFileProto ? ' Hint: Opening index.html directly with the file:// protocol blocks fetch. Run a local server, e.g. `python -m http.server` from the project directory, then visit http://localhost:8000/ .' : ' Ensure schema.json is present at the site root.';
  statusEl.innerHTML = 'Failed to load data file <code>' + dataUrl + '</code>. ' + (err && err.message ? err.message : '') + hint;
    }
  }

  init();
})();
