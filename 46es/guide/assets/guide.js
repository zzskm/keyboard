(function(){
  var KEY = document.documentElement.getAttribute("data-store") || "46es-guide";
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { state = {}; }
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  var boxes = Array.prototype.slice.call(document.querySelectorAll('input[type="checkbox"][id]'));
  function group(el){ var g = el.closest("[data-group]"); return g ? g.getAttribute("data-group") : ""; }
  function card(el){ return el.closest(".step, .issue"); }
  function update(){
    var counts = {};
    boxes.forEach(function(b){
      var g = group(b); if (!g) return;
      counts[g] = counts[g] || [0, 0];
      counts[g][1]++; if (b.checked) counts[g][0]++;
      var c = card(b); if (c) c.classList.toggle("done", b.checked);
    });
    Object.keys(counts).forEach(function(g){
      var label = document.getElementById("p-" + g), meter = document.getElementById("m-" + g);
      if (label) label.textContent = label.getAttribute("data-label") + " " + counts[g][0] + " / " + counts[g][1];
      if (meter) meter.style.width = (counts[g][1] ? 100 * counts[g][0] / counts[g][1] : 0) + "%";
    });
  }
  boxes.forEach(function(b){
    b.checked = !!state[b.id];
    b.addEventListener("change", function(){ if (b.checked) state[b.id] = true; else delete state[b.id]; save(); update(); });
  });
  var reset = document.getElementById("reset"), armed = null;
  if (reset) reset.addEventListener("click", function(){
    if (!armed){
      reset.classList.add("arm"); reset.textContent = "한 번 더 누르면 모든 체크 해제";
      armed = setTimeout(function(){ armed = null; reset.classList.remove("arm"); reset.textContent = "체크 초기화"; }, 4000);
      return;
    }
    clearTimeout(armed); armed = null;
    state = {}; save(); boxes.forEach(function(b){ b.checked = false; }); update();
    reset.classList.remove("arm"); reset.textContent = "체크 초기화";
  });
  update();

  var links = Array.prototype.slice.call(document.querySelectorAll(".bar a"));
  var secs = links.map(function(a){ return document.querySelector(a.getAttribute("href")); });
  function mark(){
    var y = window.scrollY + 80, cur = -1;
    secs.forEach(function(s, i){ if (s && s.offsetTop <= y) cur = i; });
    links.forEach(function(a, i){ a.classList.toggle("on", i === cur); });
    if (cur >= 0){ var a = links[cur], nav = a.parentNode; if (a.offsetLeft < nav.scrollLeft || a.offsetLeft + a.offsetWidth > nav.scrollLeft + nav.clientWidth) nav.scrollLeft = a.offsetLeft - 16; }
  }
  window.addEventListener("scroll", mark, { passive: true });
  mark();
})();
