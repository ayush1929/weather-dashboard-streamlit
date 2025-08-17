// app/static/hero.js
// Apple-style animated header + FIT-TEXT logic.
// Public API: initHero(element)

function initHero(el){
  const canvas = el.querySelector(".hero-canvas");
  const inner  = el.querySelector(".inner");
  const ctx = canvas.getContext("2d", {alpha:true});
  const cat = (el.dataset.cat||"sunny").toLowerCase();
  const precip = Math.max(0, parseFloat(el.dataset.precip||"0"));
  const wind = Math.max(0, parseFloat(el.dataset.wind||"0"));
  const bgUrl = el.dataset.bg||"";
  const prefersReduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // DPR + sizing
  let dpr = Math.max(1, Math.min(window.devicePixelRatio||1, 2));
  function size(){
    const r = el.getBoundingClientRect();
    canvas.width  = Math.max(1, Math.floor(r.width*dpr));
    canvas.height = Math.max(1, Math.floor(r.height*dpr));
    el.style.setProperty("--h", el.clientHeight + "px"); 
    fitHeader(); // keep font synced to container height
  }
  size();
  const ro = new ResizeObserver(size);
  ro.observe(el);

  // ----- FIT TEXT TO CONTAINER HEIGHT (one line) -----
  // Target: occupy about 28% of hero height by default (change k if you want more/less)
  function fitHeader(){
    if(!inner) return;
    inner.style.whiteSpace = "nowrap";
    inner.style.flexWrap   = "nowrap";
    const k = 0.28; // portion of hero height to fill vertically
    const target = Math.max(18, Math.min(el.clientHeight * k, 80)); // cap for sanity

    let lo = 12, hi = 96, best = 22;
    for(let i=0;i<12;i++){
      const mid = (lo + hi) / 2;
      inner.style.setProperty("--fs", mid + "px");
      const h = inner.getBoundingClientRect().height;
      if(h <= target){ best = mid; lo = mid; } else { hi = mid; }
    }
    inner.style.setProperty("--fs", best + "px");
  }

  // background image
  let bgImg = null, bgReady = false;
  if(bgUrl){
    bgImg = new Image();
    bgImg.src = bgUrl;
    bgImg.onload = ()=>{ bgReady = true; };
  }else{
    bgReady = true;
  }

  const W=()=>canvas.width, H=()=>canvas.height;

  function drawBG(){
    const w=W(), h=H();
    if(bgImg && bgReady && bgImg.naturalWidth){
      const s=Math.max(w/bgImg.naturalWidth, h/bgImg.naturalHeight);
      const dw=bgImg.naturalWidth*s, dh=bgImg.naturalHeight*s;
      const dx=(w-dw)/2, dy=(h-dh)/2;
      ctx.globalAlpha=1; ctx.drawImage(bgImg, dx, dy, dw, dh);
    }else{
      const g=ctx.createLinearGradient(0,0,0,h);
      const m = {sunny:["#182537","#0f141b"], cloudy:["#141c27","#0f141b"], rainy:["#101822","#0c131a"], snowy:["#162230","#0f151d"], storm:["#0d141a","#0a0f16"]}[cat]||["#182537","#0f141b"];
      g.addColorStop(0,m[0]); g.addColorStop(1,m[1]);
      ctx.fillStyle=g; ctx.fillRect(0,0,w,h);
    }
  }

  // --- clouds via small value-noise (photographic look) ---
  let cloudTex=null;
  function makeCloudTex(){
    const w=W(), h=H();
    const off = new OffscreenCanvas(w, h);
    const ox = off.getContext("2d");
    const img = ox.createImageData(w, h);
    function rand(x,y){ return (Math.sin(x*127.1 + y*311.7)*43758.5453)%1; }
    function lerp(a,b,t){ return a+(b-a)*t; }
    function sm(t){ return t*t*(3-2*t); }
    function noise(nx,ny){
      const ix=Math.floor(nx), iy=Math.floor(ny);
      const fx=nx-ix, fy=ny-iy;
      const a=rand(ix,iy), b=rand(ix+1,iy), c=rand(ix,iy+1), d=rand(ix+1,iy+1);
      return lerp(lerp(a,b,sm(fx)), lerp(c,d,sm(fx)), sm(fy));
    }
    function fbm(nx,ny){
      let amp=0.6, f=1.0, s=0.0;
      for(let i=0;i<5;i++){ s += amp*noise(nx*f, ny*f*0.85); f*=2.0; amp*=0.5; }
      return s;
    }
    const scale=0.0014;
    for(let y=0;y<h;y++){
      for(let x=0;x<w;x++){
        const n=fbm(x*scale,y*scale);
        const a=Math.min(255, Math.max(0, (n-0.35)*255*1.8));
        const i=(y*w+x)*4;
        img.data[i]=245; img.data[i+1]=250; img.data[i+2]=255; img.data[i+3]=a;
      }
    }
    ox.putImageData(img,0,0);
    return off;
  }

  // rain particles
  const drops=[];
  function seedRain(){
    drops.length=0;
    const n=Math.floor(W()*H()/7000 * (1.1+Math.min(1,precip/4)));
    const th=-24*Math.PI/180;
    for(let i=0;i<n;i++){
      drops.push({
        x:Math.random()*W(), y:Math.random()*H(),
        vx:Math.cos(th)*(2.6+Math.random()*1.4),
        vy:Math.sin(th)*(2.6+Math.random()*1.4),
        len:70+Math.random()*160
      });
    }
  }
  function drawRain(){
    ctx.lineCap="round";
    for(const d of drops){
      ctx.strokeStyle="rgba(170,210,255,0.9)"; ctx.lineWidth=3*dpr;
      ctx.beginPath(); ctx.moveTo(d.x,d.y); ctx.lineTo(d.x+d.vx*d.len, d.y+d.vy*d.len); ctx.stroke();

      ctx.strokeStyle="rgba(255,255,255,0.7)"; ctx.lineWidth=1.4*dpr;
      ctx.beginPath(); ctx.moveTo(d.x+0.5*dpr, d.y+0.5*dpr); ctx.lineTo(d.x+d.vx*d.len+0.5*dpr, d.y+d.vy*d.len+0.5*dpr); ctx.stroke();

      d.x += d.vx*10; d.y += d.vy*10;
      if(d.x<-60||d.x>W()+60||d.y<-60||d.y>H()+60){ d.x=Math.random()*W(); d.y=-40; }
    }
  }

  // snow particles
  const flakes=[];
  function seedSnow(){
    flakes.length=0;
    const n=Math.floor(W()*H()/12000 * 1.2) + 180;
    for(let i=0;i<n;i++){
      flakes.push({x:Math.random()*W(), y:Math.random()*H(), r:1.2+Math.random()*2.6, spd:0.35+Math.random()*0.7, drift:(Math.random()*0.6+0.2)*(wind/20+1)});
    }
  }
  function drawSnow(){
    ctx.fillStyle="rgba(255,255,255,0.96)";
    for(const f of flakes){
      ctx.beginPath(); ctx.arc(f.x,f.y,f.r*dpr,0,Math.PI*2); ctx.fill();
      ctx.fillStyle="rgba(255,255,255,0.65)";
      ctx.beginPath(); ctx.arc(f.x+f.r*0.25*dpr, f.y-f.r*0.25*dpr, f.r*0.45*dpr, 0, Math.PI*2); ctx.fill();
      ctx.fillStyle="rgba(255,255,255,0.96)";
      f.y += f.spd*3.2*dpr;
      f.x += f.drift*dpr;
      if(f.y>H()+10){ f.y=-10; f.x=Math.random()*W(); }
      if(f.x>W()+10){ f.x=-10; }
    }
  }

  // lightning flash timing (storm)
  let flashAt = performance.now() + (1800 + Math.random()*3200);
  function drawFlash(t){
    if(t>flashAt){
      const dur = 120 + Math.random()*140;
      const p = (t - flashAt)/dur;
      const a = (p < 0.5) ? p*2 : Math.max(0,1-(p-0.5)*2);
      ctx.fillStyle = "rgba(255,255,255," + (0.85*a) + ")";
      ctx.fillRect(0,0,W(),H());
      if(p>=1){ flashAt = t + (1400 + Math.random()*2800); }
    }
  }

  function drawClouds(){
    if(!cloudTex) cloudTex = makeCloudTex();
    const save = ctx.filter;
    ctx.globalCompositeOperation="soft-light";
    ctx.filter="blur(10px) contrast(110%) brightness(105%)";
    ctx.drawImage(cloudTex,0,0);
    ctx.filter="blur(16px) opacity(0.85)";
    ctx.drawImage(cloudTex,0,H()*-0.04);
    ctx.filter=save;
    ctx.globalCompositeOperation="source-over";
  }

  function reset(){
    cloudTex=null;
    if(cat==="rainy"||cat==="storm"){ seedRain(); }
    if(cat==="snowy"){ seedSnow(); }
    fitHeader();
  }
  reset();

  function loop(t){
    drawBG();
    if(cat==="sunny"){
      const cx=W()*0.14, cy=H()*0.32, r=Math.min(W(),H())*0.28;
      const g=ctx.createRadialGradient(cx,cy,r*0.2, cx,cy,r*1.05);
      g.addColorStop(0,"rgba(255,220,140,0.98)");
      g.addColorStop(0.4,"rgba(255,195,95,0.45)");
      g.addColorStop(1,"rgba(255,195,95,0.0)");
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,r*1.05,0,Math.PI*2); ctx.fill();
    }else{
      drawClouds();
    }
    if(cat==="rainy"||cat==="storm") drawRain();
    if(cat==="snowy") drawSnow();
    if(cat==="storm") drawFlash(t);
    req = requestAnimationFrame(loop);
  }

  if(prefersReduce){
    drawBG(); if(cat!=="sunny"){ drawClouds(); }
    fitHeader();
    return;
  }

  let req = requestAnimationFrame(loop);
  window.addEventListener("resize", ()=>{ reset(); }, {passive:true});
}
