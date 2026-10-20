(function () {
  "use strict";

  var SLOTS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)"];
  var MAX_PICK = SLOTS.length;
  var PAGE = 25;
  var NS = "http://www.w3.org/2000/svg";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var data;
  var picked = [];        // selected technologies, in selection order
  var slotOf = {};        // technology -> color slot; a series keeps its color while selected
  var shown = PAGE;
  var allChips = false;
  var CHIPS = 12;

  function $(id) { return document.getElementById(id); }

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function s(tag, attrs, text) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs || {}) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    return n;
  }

  function pct(x, digits) {
    if (digits == null) digits = x < 0.1 ? 1 : 0;
    return (x * 100).toFixed(digits) + "%";
  }

  function pp(x) {
    var v = (x * 100).toFixed(1);
    return (x > 0 ? "+" : x < 0 ? "−" : "") + v.replace("-", "") + " pp";
  }

  function monthLabel(key, short) {
    var p = key.split("-");
    var m = MONTHS[Number(p[1]) - 1];
    return short ? m + " ’" + p[0].slice(2) : m + " " + p[0];
  }

  function dayLabel(iso) {
    var p = iso.split("-");
    return MONTHS[Number(p[1]) - 1] + " " + Number(p[2]);
  }

  // --- tooltip ----------------------------------------------------------------

  var tip = $("tooltip");

  function showTip(x, y, title, rows) {
    tip.replaceChildren(el("div", { class: "tt-title", text: title }));
    rows.forEach(function (r) {
      var key = el("i");
      if (r.color) key.style.setProperty("--c", r.color);
      tip.appendChild(el("div", { class: "tt-row" }, [
        key, el("strong", { text: r.value }), el("span", { class: "tt-name", text: r.name }),
      ]));
    });
    tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = x + 14 + w > innerWidth - 8 ? x - w - 14 : x + 14;
    var top = Math.min(Math.max(8, y - h / 2), innerHeight - h - 8);
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = top + "px";
  }

  function hideTip() { tip.hidden = true; }

  function tipAtElement(node, title, rows) {
    var r = node.getBoundingClientRect();
    showTip(r.left + Math.min(r.width, 240), r.top + r.height / 2, title, rows);
  }

  // --- KPI tiles --------------------------------------------------------------

  function completeMonths() {
    var hn = data.hn;
    var current = data.today.slice(0, 7);
    var last = hn.months.length - 1;
    return hn.months[last] === current ? last - 1 : last;
  }

  function sparkline(values, highlight) {
    var w = 160, h = 28, max = Math.max.apply(null, values), min = Math.min.apply(null, values);
    var span = max - min || 1;
    var pts = values.map(function (v, i) {
      return [i * (w / (values.length - 1)), h - ((v - min) / span) * (h - 6) - 3];
    });
    var svg = s("svg", { viewBox: "0 0 " + w + " " + h, width: w, height: h, "aria-hidden": "true" });
    svg.appendChild(s("path", {
      d: "M" + pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join("L"),
      class: "series", style: "stroke:var(--deemph)",
    }));
    var p = pts[highlight];
    svg.appendChild(s("circle", { cx: p[0], cy: p[1], r: 4, class: "dot", style: "fill:var(--s1)" }));
    return svg;
  }

  function tile(label, value, delta, extra) {
    return el("div", { class: "figure" }, [
      el("span", { class: "figure-value", text: value }),
      el("span", { class: "figure-label", text: label }),
      delta ? el("span", { class: "figure-note", text: delta }) : null,
      extra || null,
    ]);
  }

  // --- headline: the day's finding, written from the data ------------------------

  function renderHeadline() {
    var top = data.boards.skills;
    if (!top.length) return;
    $("headline").textContent = top[0].name + " appears in " + pct(top[0].share) + " of remote developer job posts";
    var dek = [];
    if (top.length > 2) {
      dek.push(top[1].name + " and " + top[2].name + " follow, at " + pct(top[1].share) + " and " + pct(top[2].share)
        + ", across " + data.boards.total.toLocaleString("en-US") + " listings from the last " + data.boards.window_days + " days.");
    }
    var mv = data.hn.movers;
    if (mv && mv.rising.length && mv.falling.length) {
      dek.push("In Hacker News hiring threads, " + mv.rising[0].name + " gained the most ground (" + pp(mv.rising[0].delta)
        + ") and " + mv.falling[0].name + " lost the most (" + pp(mv.falling[0].delta) + ").");
    }
    $("dek").textContent = dek.join(" ");
  }

  function renderKpis() {
    var b = data.boards, hn = data.hn;
    var boards = data.sources.filter(function (x) { return (b.per_source[x.name] || 0) > 0; });
    var tiles = [tile("Remote dev jobs, last 30 days", b.total.toLocaleString("en-US"),
      "From " + boards.length + " job boards")];

    if (b.skills.length) {
      tiles.push(tile("Most requested now", b.skills[0].name,
        "In " + pct(b.skills[0].share) + " of those listings"));
    }

    if (hn.months.length > 1) {
      var i = completeMonths();
      var share = hn.remote_share[i];
      var delta = i >= 12 ? ", " + pp(share - hn.remote_share[i - 12]) + " vs a year earlier" : "";
      tiles.push(tile("HN hiring posts that mention remote", pct(share),
        monthLabel(hn.months[i]) + delta, sparkline(hn.remote_share.slice(0, i + 1), i)));

      var total = hn.posts.reduce(function (a, c) { return a + c; }, 0);
      tiles.push(tile("Hiring posts analyzed", total.toLocaleString("en-US"),
        hn.months.length + " months of Ask HN threads"));
    }
    $("kpis").replaceChildren.apply($("kpis"), tiles);
  }

  // --- most requested (horizontal bars) ----------------------------------------

  function renderBars() {
    var b = data.boards;
    var top = b.skills.slice(0, 15);
    var max = top.length ? top[0].share : 1;
    var labels = data.sources.filter(function (x) { return x.name !== "hn"; })
      .map(function (x) { return x.label; });
    $("bars-title").textContent = "The " + top.length + " most requested technologies";
    $("bars-caption").textContent = "Share of the " + b.total + " remote developer listings seen in the last "
      + b.window_days + " days that mention each one.";
    $("bars-source").textContent = "Source: " + labels.slice(0, -1).join(", ") + " and " + labels.slice(-1) + ".";

    $("bars").replaceChildren.apply($("bars"), top.map(function (k) {
      var bar = el("span", { class: "bar" });
      bar.style.width = "calc((100% - 44px) * " + (k.share / max).toFixed(4) + ")";
      var row = el("div", { class: "bar-row", tabindex: "0" }, [
        el("span", { class: "bar-name", text: k.name }),
        el("span", { class: "bar-track" }, [bar, el("span", { class: "bar-value", text: pct(k.share) })]),
      ]);
      var rows = [{ color: "var(--s1)", value: String(k.count), name: "listings" },
                  { value: pct(k.share, 1), name: "of all listings" }];
      row.addEventListener("pointermove", function (e) { showTip(e.clientX, e.clientY, k.name, rows); });
      row.addEventListener("pointerleave", hideTip);
      row.addEventListener("focus", function () { tipAtElement(bar, k.name, rows); });
      row.addEventListener("blur", hideTip);
      return row;
    }));

    $("bars-table").replaceChildren(table(
      ["Technology", "Category", { t: "Listings", num: true }, { t: "Share", num: true }],
      b.skills.map(function (k) { return [k.name, k.category, k.count, pct(k.share, 1)]; })
    ));
  }

  function table(head, rows) {
    var thead = el("thead", {}, [el("tr", {}, head.map(function (h) {
      return typeof h === "string" ? el("th", { text: h }) : el("th", { class: "num", text: h.t });
    }))]);
    var tbody = el("tbody", {}, rows.map(function (r) {
      return el("tr", {}, r.map(function (c, i) {
        var num = typeof head[i] !== "string";
        return el("td", num ? { class: "num", text: String(c) } : { text: String(c) });
      }));
    }));
    return el("table", {}, [thead, tbody]);
  }

  // --- demand over time (multi-line) --------------------------------------------

  function trendCandidates() {
    var hn = data.hn, i = completeMonths();
    return Object.keys(hn.skills)
      .filter(function (k) { return Math.max.apply(null, hn.skills[k]) >= 0.02; })
      .sort(function (a, b) { return hn.skills[b][i] - hn.skills[a][i]; });
  }

  function defaultPicks(candidates) {
    var picks = candidates.slice(0, 3);
    var movers = data.hn.movers;
    var riser = movers && movers.rising.find(function (r) { return picks.indexOf(r.name) < 0; });
    if (riser) picks.push(riser.name);
    return picks;
  }

  function togglePick(name) {
    var at = picked.indexOf(name);
    if (at >= 0) {
      picked.splice(at, 1);
      delete slotOf[name];
    } else if (picked.length < MAX_PICK) {
      var used = picked.map(function (p) { return slotOf[p]; });
      slotOf[name] = [0, 1, 2, 3].find(function (n) { return used.indexOf(n) < 0; });
      picked.push(name);
    }
    renderPicker();
    renderTrend();
  }

  function renderPicker() {
    var full = picked.length >= MAX_PICK;
    var candidates = trendCandidates();
    var visible = allChips ? candidates : candidates.filter(function (name, i) {
      return i < CHIPS || picked.indexOf(name) >= 0;
    });
    var chips = visible.map(function (name) {
      var on = picked.indexOf(name) >= 0;
      var key = el("i", { class: "key" });
      if (on) key.style.setProperty("--c", SLOTS[slotOf[name]]);
      var chip = el("button", { type: "button", class: "chip", "aria-pressed": String(on) },
        [key, document.createTextNode(name)]);
      chip.disabled = full && !on;
      chip.addEventListener("click", function () { togglePick(name); });
      return chip;
    });
    if (candidates.length > visible.length || allChips) {
      var toggle = el("button", { type: "button", class: "chip chip-more",
        text: allChips ? "Show fewer" : "Show all " + candidates.length });
      toggle.addEventListener("click", function () { allChips = !allChips; renderPicker(); });
      chips.push(toggle);
    }
    $("picker").replaceChildren.apply($("picker"), chips);
  }

  function niceMax(v) {
    var step = v > 0.3 ? 0.1 : v > 0.12 ? 0.05 : v > 0.05 ? 0.02 : 0.01;
    return { max: Math.max(step, Math.ceil(v / step) * step), step: step };
  }

  function renderTrend() {
    var hn = data.hn, box = $("trend");
    var W = box.clientWidth, narrow = W < 560;
    var H = narrow ? 240 : 290;
    var m = { top: 12, right: narrow ? 88 : 120, bottom: 28, left: 40 };
    var iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    var n = hn.months.length;
    var series = picked.map(function (name) {
      return { name: name, color: SLOTS[slotOf[name]], values: hn.skills[name] };
    });
    var peak = Math.max.apply(null, [0.01].concat(series.map(function (x) { return Math.max.apply(null, x.values); })));
    var scale = niceMax(peak);
    var x = function (i) { return m.left + (n === 1 ? iw / 2 : (i * iw) / (n - 1)); };
    var y = function (v) { return m.top + ih - (v / scale.max) * ih; };

    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, height: H, tabindex: "0", role: "img",
      "aria-label": "Line chart: share of HN hiring posts mentioning " + picked.join(", ") + ", by month. Use the arrow keys to read values." });

    for (var t = 0; t <= scale.max + 1e-9; t += scale.step) {
      svg.appendChild(s("line", { x1: m.left, x2: m.left + iw, y1: y(t), y2: y(t),
        class: t === 0 ? "baseline" : "gridline" }));
      svg.appendChild(s("text", { x: m.left - 8, y: y(t) + 4, "text-anchor": "end" }, pct(t, 0)));
    }

    var every = Math.ceil(n / Math.max(2, Math.floor(iw / 64)));
    hn.months.forEach(function (key, i) {
      if ((n - 1 - i) % every === 0) {
        svg.appendChild(s("text", { x: x(i), y: H - 8, "text-anchor": "middle" }, monthLabel(key, true)));
      }
    });

    series.forEach(function (sr) {
      var d = sr.values.map(function (v, i) { return (i ? "L" : "M") + x(i).toFixed(1) + "," + y(v).toFixed(1); }).join("");
      svg.appendChild(s("path", { d: d, class: "series", style: "stroke:" + sr.color }));
    });

    // End labels: placed at each line's last value, pushed apart when lines converge,
    // with a leader line back to the end dot when a label had to move.
    var ends = series.map(function (sr) {
      var v = sr.values[n - 1];
      return { sr: sr, y0: y(v), y: y(v), v: v };
    }).sort(function (a, b) { return a.y0 - b.y0; });
    var gap = 16;
    for (var k = 1; k < ends.length; k++) ends[k].y = Math.max(ends[k].y, ends[k - 1].y + gap);
    var overflow = ends.length ? ends[ends.length - 1].y - (m.top + ih) : 0;
    if (overflow > 0) ends.forEach(function (e) { e.y -= overflow; });
    for (k = ends.length - 2; k >= 0; k--) ends[k].y = Math.min(ends[k].y, ends[k + 1].y - gap);
    ends.forEach(function (e) {
      var lx = x(n - 1) + 12;
      if (Math.abs(e.y - e.y0) > 2) {
        svg.appendChild(s("path", { d: "M" + (x(n - 1) + 6) + "," + e.y0 + "L" + (lx - 3) + "," + e.y, class: "leader" }));
      }
      svg.appendChild(s("circle", { cx: x(n - 1), cy: e.y0, r: 4, class: "dot", style: "fill:" + e.sr.color }));
      svg.appendChild(s("text", { x: lx, y: e.y + 4, class: "end-label" }, e.sr.name + " " + pct(e.v)));
    });

    // Hover layer: a crosshair that snaps to the nearest month, one tooltip for every series.
    var hover = s("g", { visibility: "hidden" });
    var cross = s("line", { y1: m.top, y2: m.top + ih, class: "crosshair" });
    hover.appendChild(cross);
    var dots = series.map(function (sr) {
      var c = s("circle", { r: 4, class: "dot", style: "fill:" + sr.color });
      hover.appendChild(c);
      return c;
    });
    svg.appendChild(hover);
    var hit = s("rect", { x: m.left, y: m.top, width: Math.max(iw, 0), height: ih, fill: "transparent" });
    svg.appendChild(hit);

    var active = n - 1;
    function show(i, cx, cy) {
      active = i;
      hover.setAttribute("visibility", "visible");
      cross.setAttribute("x1", x(i));
      cross.setAttribute("x2", x(i));
      series.forEach(function (sr, j) {
        dots[j].setAttribute("cx", x(i));
        dots[j].setAttribute("cy", y(sr.values[i]));
      });
      var rows = series.map(function (sr) { return { color: sr.color, value: pct(sr.values[i], 1), name: sr.name, v: sr.values[i] }; })
        .sort(function (a, b) { return b.v - a.v; });
      rows.push({ value: String(hn.posts[i]), name: "posts that month" });
      if (cx == null) {
        var r = svg.getBoundingClientRect(), ratio = r.width / W;
        cx = r.left + x(i) * ratio;
        cy = r.top + m.top * ratio + 40;
      }
      showTip(cx, cy, monthLabel(hn.months[i]), rows);
    }
    function hide() { hover.setAttribute("visibility", "hidden"); hideTip(); }

    hit.addEventListener("pointermove", function (e) {
      var r = svg.getBoundingClientRect();
      var px = (e.clientX - r.left) * (W / r.width);
      var i = Math.round(((px - m.left) / iw) * (n - 1));
      show(Math.max(0, Math.min(n - 1, i)), e.clientX, e.clientY);
    });
    hit.addEventListener("pointerleave", hide);
    svg.addEventListener("focus", function () { show(active); });
    svg.addEventListener("blur", hide);
    svg.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault();
        show(Math.max(0, Math.min(n - 1, active + (e.key === "ArrowLeft" ? -1 : 1))));
      }
    });

    box.replaceChildren(svg);

    var legend = series.map(function (sr) {
      var key = el("i");
      key.style.setProperty("--c", sr.color);
      return el("span", {}, [key, document.createTextNode(sr.name)]);
    });
    $("trend-legend").replaceChildren.apply($("trend-legend"), legend);

    var last = hn.months[n - 1];
    $("trend-note").textContent = last === data.today.slice(0, 7)
      ? monthLabel(last) + " is still in progress: its thread opened on the 1st and keeps growing."
      : "";

    $("trend-table").replaceChildren(table(
      ["Month", { t: "Posts", num: true }].concat(picked.map(function (p) { return { t: p, num: true }; })),
      hn.months.map(function (key, i) {
        return [monthLabel(key), hn.posts[i]].concat(picked.map(function (p) { return pct(hn.skills[p][i], 1); }));
      })
    ));
  }

  // --- rising and falling (diverging bars) ----------------------------------------

  function barPath(x0, x1, top, h) {
    var w = Math.abs(x1 - x0), r = Math.min(4, w, h / 2), dir = x1 >= x0 ? 1 : -1;
    var e = x1 - dir * r;
    return "M" + x0 + "," + top + "H" + e
      + "A" + r + "," + r + " 0 0 " + (dir > 0 ? 1 : 0) + " " + x1 + "," + (top + r)
      + "V" + (top + h - r)
      + "A" + r + "," + r + " 0 0 " + (dir > 0 ? 1 : 0) + " " + e + "," + (top + h)
      + "H" + x0 + "Z";
  }

  function renderMovers() {
    var mv = data.hn.movers;
    $("movers-card").hidden = !mv;
    if (!mv) return;
    var rows = mv.rising.concat(mv.falling.slice().reverse());
    var range = function (keys) { return monthLabel(keys[0]).split(" ")[0] + "–" + monthLabel(keys[keys.length - 1]); };
    if (mv.rising.length && mv.falling.length) {
      $("movers-title").textContent = mv.rising[0].name + " is rising fastest; " + mv.falling[0].name + " is losing the most ground";
    }
    $("movers-caption").textContent = "Change in the share of HN hiring posts that mention each technology, "
      + range(mv.now) + " vs " + range(mv.before) + ". Only technologies in at least 2% of posts.";

    var box = $("movers"), W = box.clientWidth, narrow = W < 560;
    var labelW = narrow ? 96 : 130, valueW = 64, rowH = 28, barH = 16;
    var H = rows.length * rowH + 8;
    var plotL = labelW + valueW, plotR = W - valueW;
    var mid = (plotL + plotR) / 2, half = (plotR - plotL) / 2;
    var maxAbs = Math.max.apply(null, rows.map(function (r) { return Math.abs(r.delta); })) || 1;

    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, height: H, role: "img",
      "aria-label": "Diverging bar chart of the technologies whose share of hiring posts rose or fell the most." });
    rows.forEach(function (r, i) {
      var top = i * rowH + 4, cy = top + rowH / 2;
      var end = mid + (r.delta / maxAbs) * half;
      var up = r.delta >= 0;
      var hit = s("rect", { x: 0, y: top, width: W, height: rowH, rx: 6, class: "hit", tabindex: "0" });
      svg.appendChild(hit);
      svg.appendChild(s("text", { x: 0, y: cy + 4, class: "label" }, r.name));
      svg.appendChild(s("path", { d: barPath(mid, end, cy - barH / 2, barH), style: "fill:var(" + (up ? "--up" : "--down") + ")" }));
      svg.appendChild(s("text", { x: up ? end + 6 : end - 6, y: cy + 4, class: "value", "text-anchor": up ? "start" : "end" }, pp(r.delta)));
      var tipRows = [
        { color: "var(" + (up ? "--up" : "--down") + ")", value: pp(r.delta), name: "change" },
        { value: pct(r.now, 1), name: range(mv.now) },
        { value: pct(r.before, 1), name: range(mv.before) },
      ];
      hit.addEventListener("pointermove", function (e) { showTip(e.clientX, e.clientY, r.name, tipRows); });
      hit.addEventListener("pointerleave", hideTip);
      hit.addEventListener("focus", function () {
        var b = hit.getBoundingClientRect();
        showTip(b.left + b.width / 2, b.top + b.height / 2, r.name, tipRows);
      });
      hit.addEventListener("blur", hideTip);
    });
    svg.appendChild(s("line", { x1: mid, x2: mid, y1: 0, y2: H, class: "baseline" }));
    box.replaceChildren(svg);

    $("movers-table").replaceChildren(table(
      ["Technology", { t: range(mv.before), num: true }, { t: range(mv.now), num: true }, { t: "Change", num: true }],
      rows.map(function (r) { return [r.name, pct(r.before, 1), pct(r.now, 1), pp(r.delta)]; })
    ));
  }

  // --- latest listings ------------------------------------------------------------

  function renderJobs() {
    var q = $("search").value.trim().toLowerCase();
    var label = {};
    data.sources.forEach(function (x) { label[x.name] = x.label; });
    var list = data.boards.latest.filter(function (j) {
      if (!q) return true;
      return [j.title, j.company, label[j.source]].concat(j.skills).join(" ").toLowerCase().indexOf(q) >= 0;
    });

    var head = el("thead", {}, [el("tr", {}, [
      el("th", { text: "Job" }), el("th", { text: "Technologies" }),
      el("th", { text: "Source" }), el("th", { text: "Posted" }),
    ])]);
    var body = el("tbody", {}, list.slice(0, shown).map(function (j) {
      var tags = j.skills.slice(0, 6).map(function (t) { return el("span", { text: t }); });
      if (j.skills.length > 6) tags.push(el("span", { text: "+" + (j.skills.length - 6) }));
      return el("tr", {}, [
        el("td", {}, [
          el("a", { href: j.url, target: "_blank", rel: "noopener", text: j.title }),
          el("div", { class: "company", text: [j.company, j.location].filter(Boolean).join(" · ") }),
        ]),
        el("td", {}, [el("div", { class: "tags" }, tags)]),
        el("td", { class: "source", text: label[j.source] || j.source }),
        el("td", { class: "date", text: j.posted_at ? dayLabel(j.posted_at) : "" }),
      ]);
    }));
    if (!list.length) {
      body.appendChild(el("tr", {}, [el("td", { colspan: "4", text: "No listings match “" + q + "”." })]));
    }
    $("jobs").replaceChildren(head, body);
    $("more").hidden = list.length <= shown;
  }

  // --- page -------------------------------------------------------------------------

  function renderMeta() {
    var d = new Date(data.generated_at);
    $("updated").textContent = d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
    var p = $("sources");
    p.replaceChildren(document.createTextNode("Data: "));
    data.sources.forEach(function (x, i) {
      if (i) p.appendChild(document.createTextNode(i === data.sources.length - 1 ? " and " : ", "));
      p.appendChild(el("a", { href: x.url, target: "_blank", rel: "noopener", text: x.label }));
    });
    p.appendChild(document.createTextNode(" (via the Algolia HN API). Job links go to the original post on each board."));
  }

  function renderAll() {
    renderMeta();
    renderHeadline();
    renderKpis();
    renderBars();
    if (data.hn.months.length) {
      var candidates = trendCandidates();
      defaultPicks(candidates).forEach(togglePick);
    }
    renderMovers();
    renderJobs();
  }

  var pending = 0;
  function onResize() {
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(function () {
      if (!data) return;
      if (data.hn.months.length) renderTrend();
      renderMovers();
    });
  }

  $("search").addEventListener("input", function () { shown = PAGE; renderJobs(); });
  $("more").addEventListener("click", function () { shown += PAGE; renderJobs(); });
  $("theme").addEventListener("click", function () {
    var root = document.documentElement;
    var cur = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.dataset.theme = cur === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  });
  new ResizeObserver(onResize).observe($("app"));

  fetch("data/summary.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (json) {
      data = json;
      renderAll();
      $("app").removeAttribute("aria-busy");
    })
    .catch(function (err) {
      $("app").removeAttribute("aria-busy");
      $("app").replaceChildren(el("p", { class: "card", text: "Could not load the data (" + err.message + ")." }));
    });
})();
