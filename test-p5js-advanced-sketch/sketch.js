let particles = [];
let attractors = [];

const PARTICLE_COUNT = 300;
const MAX_SPEED = 4;

function setup() {
  createCanvas(800, 600);
  colorMode(HSB, 360, 100, 100, 100);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
  }
}

function draw() {
  background(0, 0, 8, 2);

  updateParticles();
  drawParticles();
  drawAttractors();
  drawInfo();
}

function mouseClicked() {
  if (mouseButton === LEFT) {
    attractors.push(createVector(mouseX, mouseY, 1));  // z=1 for attract
  } else if (mouseButton === RIGHT) {
    attractors.push(createVector(mouseX, mouseY, -1)); // z=-1 for repel
  }
}

function keyPressed() {
  if (key === 'c' || key === 'C') attractors = [];
}

function drawAttractors() {
  for (let i = attractors.length - 1; i >= 0; i--) {
    const a = attractors[i];
    const age = frameCount - (a._birth || (a._birth = frameCount));
    if (age > 120) { attractors.splice(i, 1); continue; }

    const alpha = map(age, 0, 120, 80, 0);
    const hue = a.z === 1 ? 200 : 0;
    fill(hue, 80, 90, alpha);
    noStroke();
    const r = map(age, 0, 120, 25, 5);
    circle(a.x, a.y, r * 2);
  }
}

function updateParticles() {
  for (const p of particles) {
    applyAttractors(p);
    p.vel.limit(MAX_SPEED);
    p.pos.add(p.vel);
    p.vel.mult(0.98);

    if (p.pos.x < 0) p.pos.x = width;
    if (p.pos.x > width) p.pos.x = 0;
    if (p.pos.y < 0) p.pos.y = height;
    if (p.pos.y > height) p.pos.y = 0;

    p.trail.push(p.pos.copy());
    if (p.trail.length > 12) p.trail.shift();
  }
}

function applyAttractors(pt) {
  for (const a of attractors) {
    const dx = a.x - pt.pos.x;
    const dy = a.y - pt.pos.y;
    const d = sqrt(dx * dx + dy * dy);
    if (d < 1) continue;
    const strength = a.z * 80;
    pt.vel.x += (dx / d) * strength / d;
    pt.vel.y += (dy / d) * strength / d;
  }
}

function drawParticles() {
  for (const p of particles) {
    drawNeighbors(p);

    if (p.trail.length > 1) {
      noFill();
      for (let i = 1; i < p.trail.length; i++) {
        const alpha = map(i, 0, p.trail.length, 0, 40);
        stroke(p.hue, 70, 90, alpha);
        strokeWeight(p.size * 0.4);
        line(p.trail[i - 1].x, p.trail[i - 1].y, p.trail[i].x, p.trail[i].y);
      }
    }

    fill(p.hue, 80, 95, 80);
    noStroke();
    circle(p.pos.x, p.pos.y, p.size);
  }
}

function drawNeighbors(p) {
  for (const other of particles) {
    if (other === p) continue;
    const d = dist(p.pos.x, p.pos.y, other.pos.x, other.pos.y);
    if (d < 60) {
      const alpha = map(d, 0, 60, 60, 0);
      stroke(260, 50, 90, alpha);
      strokeWeight(0.5);
      line(p.pos.x, p.pos.y, other.pos.x, other.pos.y);
    }
  }
}

function drawInfo() {
  fill(0, 0, 100, 80);
  noStroke();
  textAlign(LEFT, TOP);
  textSize(13);
  text("particles: " + PARTICLE_COUNT, 12, 12);
  text("attractors: " + attractors.length, 12, 30);
  textSize(11);
  text("[left-click] attract  [right-click] repel  [c] clear", 12, 52);
  text("p5.js advanced sketch embedded in Streamlit", 12, height - 16);
}

class Particle {
  constructor() {
    this.pos = createVector(random(width), random(height));
    this.vel = createVector(random(-1, 1), random(-1, 1));
    this.size = random(2, 5);
    this.hue = random(360);
    this.trail = [];
  }
}
