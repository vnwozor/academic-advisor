const form = document.getElementById("habits");
const $ = (id) => document.getElementById(id);
const NAMES = {
  prev_cgpa: ["CGPA so far", (v) => v.toFixed(2)],
  attendance: ["Attendance", (v) => v + "%"],
  study_hours: ["Study hours", (v) => v + " hrs/wk"],
  assignments_done: ["Assignments", (v) => v + "%"],
  ca_score: ["CA score", (v) => v + "/30"],
  course_units: ["Units", (v) => v + " units"],
  sleep_hours: ["Sleep", (v) => v + " hrs"],
};
const pos = (v, min, max) => ((v - min) / (max - min)) * 100 + "%";

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function renderStats(r) {
  // likely range on the main scale
  const range = $("range");
  range.style.setProperty("--lo", (r.range[0] / 5) * 100 + "%");
  range.style.setProperty("--hi", (r.range[1] / 5) * 100 + "%");
  $("range-text").textContent = `${r.range[0].toFixed(2)} – ${r.range[1].toFixed(2)}`;

  // you vs other students
  const list = $("compare");
  list.replaceChildren();
  for (const c of r.compare) {
    const [label, f] = NAMES[c.field];
    const li = el("li");
    const name = el("span", "c-name", label);
    name.append(el("small", null, `you ${f(c.value)}, typical ${f(Math.round(c.median * 10) / 10)}`));
    const pct = el("span", "c-pct", `Higher than ${c.percentile}%`);
    const track = el("div", "c-track");
    track.title = `${label}: you ${f(c.value)}, middle half of students ${f(c.p25)}–${f(c.p75)}`;
    const iqr = el("span", "c-iqr");
    iqr.style.left = pos(c.p25, c.min, c.max);
    iqr.style.width = `calc(${pos(c.p75, c.min, c.max)} - ${pos(c.p25, c.min, c.max)})`;
    const med = el("span", "c-med");
    med.style.left = pos(c.median, c.min, c.max);
    const you = el("span", "c-you");
    you.style.left = pos(c.value, c.min, c.max);
    track.append(iqr, med, you);
    li.append(name, pct, track);
    list.append(li);
  }

  // standing probabilities
  const probs = $("probability");
  probs.replaceChildren();
  for (const level of ["On track", "Needs attention", "At risk"]) {
    const p = r.probability[level] ?? 0;
    const li = el("li");
    li.dataset.level = level;
    const bar = el("span", "p-bar");
    const fill = el("i");
    fill.style.width = p * 100 + "%";
    bar.append(fill);
    li.append(el("span", "p-name", level), el("span", "p-val", Math.round(p * 100) + "%"), bar);
    probs.append(li);
  }

  // feature importance (drawn once; it doesn't change per student)
  const imp = $("importance");
  if (!imp.children.length) {
    const top = r.importance[0].weight;
    for (const i of r.importance) {
      const li = el("li");
      const bar = el("span", "imp-bar");
      bar.style.width = (i.weight / top) * 100 + "%";
      bar.title = `${NAMES[i.field][0]}: ${(i.weight * 100).toFixed(1)}% of the model's decisions`;
      const track = el("span", "imp-track");
      track.append(bar);
      li.append(el("span", null, NAMES[i.field][0]), track,
                el("span", "imp-val", Math.round(i.weight * 100) + "%"));
      imp.append(li);
    }
  }
}

const BANDS = [[4.5, "1st"], [3.5, "2:1"], [2.4, "2:2"], [1.5, "3rd"], [1.0, "P"], [0, "F"]];

function fmt(input) {
  const v = Number(input.value);
  return input.step.includes(".") && input.name === "prev_cgpa" ? v.toFixed(2) : String(v);
}

function syncLabels() {
  for (const input of form.querySelectorAll("input[type=range]")) {
    const out = form.querySelector(`output[data-for="${input.name}"]`);
    out.textContent = fmt(input) + (out.dataset.unit || "");
    const pct = ((input.value - input.min) / (input.max - input.min)) * 100;
    input.style.setProperty("--fill", pct + "%");
  }
}

function place(pin, cgpa) {
  pin.querySelector("em").textContent = cgpa.toFixed(2);
  const pct = (cgpa / 5) * 100;
  pin.style.setProperty("--at", pct + "%");
  const label = pin.querySelector("b");
  label.style.transform =
    pct < 10 ? "translateX(-8px)" : pct > 90 ? "translateX(calc(-100% + 8px))" : "translateX(-50%)";
}

function render(r, prev) {
  $("projected").textContent = r.projected_cgpa.toFixed(2);
  $("degree").textContent = r.degree_class;
  const st = $("standing");
  st.textContent = r.standing;
  st.dataset.level = r.standing;

  renderStats(r);
  place($("pin-now"), r.projected_cgpa);
  place($("pin-prev"), prev);
  const reach = $("pin-reach");
  reach.hidden = r.potential_cgpa - r.projected_cgpa < 0.05;
  place(reach, r.potential_cgpa);

  const band = BANDS.find(([floor]) => r.projected_cgpa >= floor)[1];
  document.querySelectorAll(".bands span").forEach((s) => s.classList.toggle("here", s.dataset.l === band));

  const list = $("tips");
  list.replaceChildren();
  if (r.tips.length === 0) {
    $("advice-title").textContent = "Keep doing what you're doing";
    $("reach").textContent = "None of your habits has an obvious gap. Protect your routine through exams.";
    return;
  }
  $("advice-title").textContent = "What would help most";
  for (const t of r.tips) {
    const li = document.createElement("li");
    li.innerHTML = `<h3></h3><span class="gain"></span><p></p>`;
    li.querySelector("h3").textContent = t.title;
    li.querySelector(".gain").textContent = "+" + t.gain.toFixed(2);
    li.querySelector("p").textContent = t.detail;
    list.append(li);
  }
  const reachNote = $("reach");
  reachNote.innerHTML = "";
  if (r.potential_cgpa > r.projected_cgpa) {
    reachNote.append("Do all of these and the model puts you at ");
    const s = document.createElement("strong");
    s.textContent = `${r.potential_cgpa.toFixed(2)} (${r.potential_class})`;
    reachNote.append(s, ".");
  }
}

let timer, controller;
async function update() {
  const data = Object.fromEntries(new FormData(form));
  controller?.abort();
  controller = new AbortController();
  try {
    const res = await fetch("/api/advise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal: controller.signal,
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || "The advisor couldn't read those values.");
    $("error").hidden = true;
    render(body, Number(data.prev_cgpa));
  } catch (err) {
    if (err.name === "AbortError") return;
    $("error").textContent = err.message.includes("fetch")
      ? "Can't reach the advisor. Check that app.py is still running."
      : err.message;
    $("error").hidden = false;
  }
}

form.addEventListener("input", () => {
  syncLabels();
  clearTimeout(timer);
  timer = setTimeout(update, 160);
});
form.addEventListener("submit", (e) => { e.preventDefault(); update(); });

syncLabels();
update();
