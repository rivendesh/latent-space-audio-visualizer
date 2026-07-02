const sketch = (p) => {
  let particles = [];
  let attractors = [];
  let starField = [];
  let flowField = [];

  const PARTICLE_COUNT = 300;
  const STAR_COUNT = 200;
  const MAX_SPEED = 4;

  p.setup = () => {
    p.createCanvas(800, 600);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(new Particle(p));
    }

    for (let i = 0; i < STAR_COUNT; i++) {
      starField.push({
        x: p.random(p.width),
        y: p.random(p.height),
        size: p.random(0.5, 2.5),
        twinkleSpeed: p.random(0.01, 0.05),
        phase: p.random(p.TWO_PI),
      });
    }

    const cols = p.floor(p.width / 20);
    const rows = p.floor(p.height / 20);
    for (let i = 0; i < cols * rows; i++) {
      flowField.push(p.random(p.TWO_PI));
    }
  };

  p.draw = () => {
    p.background(10, 8, 20, 40);

    drawStars(p);
    updateAndDrawParticles(p);
    drawAttractors(p);
    drawInfo(p);
  };

  p.mouseClicked = () => {
    if (p.mouseButton === p.LEFT) {
      attractors.push({
        x: p.mouseX,
        y: p.mouseY,
        strength: 100,
        life: 255,
        type: 'attract',
      });
    } else if (p.mouseButton === p.RIGHT) {
      attractors.push({
        x: p.mouseX,
        y: p.mouseY,
        strength: -150,
        life: 255,
        type: 'repel',
      });
    }
  };

  p.mousePressed = () => {
    if (p.mouseButton === p.CENTER) {
      attractors = [];
    }
  };

  function drawStars(p) {
    for (const star of starField) {
      const alpha = 128 + 127 * p.sin(p.frameCount * star.twinkleSpeed + star.phase);
      p.fill(255, alpha);
      p.noStroke();
      p.circle(star.x, star.y, star.size);
    }
  }

  function drawAttractors(p) {
    for (let i = attractors.length - 1; i >= 0; i--) {
      const a = attractors[i];
      a.life -= 2;
      if (a.life <= 0) {
        attractors.splice(i, 1);
        continue;
      }
      const alpha = p.map(a.life, 255, 0, 80, 0);
      const r = a.type === 'attract' ? p.color(100, 200, 255, alpha) : p.color(255, 100, 100, alpha);
      p.fill(r);
      p.noStroke();
      const radius = p.map(a.life, 255, 0, 30, 5);
      p.circle(a.x, a.y, radius * 2);
    }
  }

  function updateAndDrawParticles(p) {
    for (const pt of particles) {
      applyAttractors(p, pt);
      applyFlowField(p, pt);

      const neighbors = findNeighbors(pt, particles, 60);
      for (const n of neighbors) {
        const alpha = p.map(p.dist(pt.pos.x, pt.pos.y, n.pos.x, n.pos.y), 0, 60, 100, 0);
        p.stroke(180, 140, 255, alpha);
        p.strokeWeight(0.5);
        p.line(pt.pos.x, pt.pos.y, n.pos.x, n.pos.y);
      }

      pt.update();
      pt.show(p);
    }
  }

  function applyAttractors(p, pt) {
    for (const a of attractors) {
      const dx = a.x - pt.pos.x;
      const dy = a.y - pt.pos.y;
      const dist = p.sqrt(dx * dx + dy * dy);
      if (dist < 1) continue;
      const force = (a.strength / (dist * dist)) * 0.5;
      pt.vel.x += (dx / dist) * force;
      pt.vel.y += (dy / dist) * force;
    }
  }

  function applyFlowField(p, pt) {
    const col = p.floor(pt.pos.x / 20);
    const row = p.floor(pt.pos.y / 20);
    const cols = p.floor(p.width / 20);
    const idx = p.constrain(col + row * cols, 0, flowField.length - 1);
    const angle = flowField[idx] + p.sin(p.frameCount * 0.005 + idx) * 0.3;
    pt.vel.x += p.cos(angle) * 0.1;
    pt.vel.y += p.sin(angle) * 0.1;
  }

  function findNeighbors(pt, all, radius) {
    const result = [];
    for (const other of all) {
      if (other === pt) continue;
      const d = p.dist(pt.pos.x, pt.pos.y, other.pos.x, other.pos.y);
      if (d < radius) result.push(other);
    }
    return result;
  }

  function drawInfo(p) {
    p.fill(255, 180);
    p.noStroke();
    p.textAlign(p.LEFT, p.TOP);
    p.textSize(13);
    p.text(`Particles: ${PARTICLE_COUNT}`, 12, 12);
    p.text(`Attractors: ${attractors.length}`, 12, 30);
    p.text("Left-click: attract  |  Right-click: repel  |  Middle-click: clear", 12, 52);
    p.textSize(11);
    p.text("p5.js advanced sketch embedded in Streamlit", 12, p.height - 16);
  }
};

class Particle {
  constructor(p) {
    this.pos = p.createVector(p.random(p.width), p.random(p.height));
    this.vel = p.createVector(p.random(-1, 1), p.random(-1, 1));
    this.acc = p.createVector(0, 0);
    this.size = p.random(2, 5);
    this.hue = p.random(360);
    this.trail = [];
  }

  update() {
    this.vel.add(this.acc);
    this.vel.limit(MAX_SPEED);
    this.pos.add(this.vel);
    this.acc.mult(0);

    this.trail.push({ x: this.pos.x, y: this.pos.y });
    if (this.trail.length > 8) this.trail.shift();

    if (this.pos.x < 0) this.pos.x = 800;
    if (this.pos.x > 800) this.pos.x = 0;
    if (this.pos.y < 0) this.pos.y = 600;
    if (this.pos.y > 600) this.pos.y = 0;

    this.hue = (this.hue + 0.3) % 360;
  }

  show(p) {
    if (this.trail.length > 1) {
      p.noFill();
      for (let i = 1; i < this.trail.length; i++) {
        const alpha = p.map(i, 0, this.trail.length, 0, 60);
        p.stroke(this.hue, 180, 220, alpha);
        p.strokeWeight(this.size * 0.5);
        p.line(this.trail[i - 1].x, this.trail[i - 1].y, this.trail[i].x, this.trail[i].y);
      }
    }

    p.colorMode(p.HSB);
    p.fill(this.hue, 200, 255, 200);
    p.noStroke();
    p.circle(this.pos.x, this.pos.y, this.size);
    p.colorMode(p.RGB);
  }
}
