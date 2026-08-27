/*
 * SentinelDNS — Landing 3-D Torus Renderer
 *
 * Renders 34 iridescent blade-petals arranged in a torus ring.
 * All 3-D math is pure canvas 2-D — no libraries.
 *
 * Pipeline each frame:
 *   1. Scale design-unit blade corners to pixel space (sc factor)
 *   2. Apply global Y-rotation (animation) + X-tilt (perspective + mouse)
 *   3. Perspective-project to canvas 2-D
 *   4. Sort blades back-to-front (painter's algorithm)
 *   5. Draw each blade: linear gradient (dark inner → bright outer)
 *      + warm white-gold stroke on lit outer edges
 *   6. Draw orbital rings, revolving particles, sensor badges, and
 *      a starfield around the torus
 */

(() => {
  'use strict';

  const canvas = document.getElementById('hero-canvas');
  if (!canvas) return;

  const ctx   = canvas.getContext('2d');
  const scene = canvas.parentElement;
  const RM    = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── State ──────────────────────────────────────────────── */

  let W, H, CX, CY, sc;

  let rotY    = 0;
  const ROT_SPEED = RM ? 0 : 0.0032;   // rad/frame, full turn ~12 s at 60 fps
  const BASE_RX   = -0.30;             // constant downward-view tilt

  // Smoothed mouse position (normalised 0–1 over window)
  let smX = 0.5, smY = 0.5, tgX = 0.5, tgY = 0.5;

  let raf = null;
  let ts0 = null;  // timestamp anchor for particle time

  /* ── Torus config (design units — all scaled by sc at render time) ── */

  const N        = 34;    // blade count
  const TILT     = 0.72;  // blade tilt around radial axis (rad)
  const D_INNER  = 50;    // inner blade edge radius
  const D_OUTER  = 148;   // outer blade edge radius
  const D_HALF_W = 16;    // blade half-width at outer edge

  // Perspective constants (in px, independent of sc)
  const FOCAL  = 420;
  const CAM_Z  = 380;

  // Light direction (unit vector) — upper-front, slightly right
  const LX = 0.300, LY = 0.699, LZ = -0.650;

  /* ── Precomputed blade data (constant; only N + TILT matter) ── */

  let bladeBase = [];

  function precomputeBlades() {
    bladeBase = [];
    const cosT = Math.cos(TILT), sinT = Math.sin(TILT);

    for (let i = 0; i < N; i++) {
      const θ  = (2 * Math.PI * i) / N;
      const cθ = Math.cos(θ), sθ = Math.sin(θ);

      // Local frame at this ring position
      const rd = [cθ, 0, sθ];                      // radial direction
      const wd = [-sinT * sθ, cosT, sinT * cθ];    // tilted width direction

      // Tapered blade: inner tip is narrow, outer edge is full width
      const iHW = D_HALF_W * 0.28;   // inner half-width
      const oHW = D_HALF_W * 1.00;   // outer half-width

      // 4 corners (design units, un-scaled)
      //  c[0] = inner-left,  c[1] = inner-right
      //  c[2] = outer-right, c[3] = outer-left
      bladeBase.push({
        c: [
          [rd[0]*D_INNER - wd[0]*iHW, rd[1]*D_INNER - wd[1]*iHW, rd[2]*D_INNER - wd[2]*iHW],
          [rd[0]*D_INNER + wd[0]*iHW, rd[1]*D_INNER + wd[1]*iHW, rd[2]*D_INNER + wd[2]*iHW],
          [rd[0]*D_OUTER + wd[0]*oHW, rd[1]*D_OUTER + wd[1]*oHW, rd[2]*D_OUTER + wd[2]*oHW],
          [rd[0]*D_OUTER - wd[0]*oHW, rd[1]*D_OUTER - wd[1]*oHW, rd[2]*D_OUTER - wd[2]*oHW],
        ],
        // Unit face normal (analytically derived: normalised cross of wd × rd)
        n: [cosT * sθ, sinT, -cosT * cθ],
        t: i / N,   // normalised ring position 0–1 (drives hue)
      });
    }
  }

  /* ── 3-D rotation helpers ────────────────────────────────── */

  function ry3(p, a) {
    const [x, y, z] = p, c = Math.cos(a), s = Math.sin(a);
    return [x * c + z * s, y, -x * s + z * c];
  }

  function rx3(p, a) {
    const [x, y, z] = p, c = Math.cos(a), s = Math.sin(a);
    return [x, y * c - z * s, y * s + z * c];
  }

  /* ── Perspective projection ──────────────────────────────── */
  // Input: world-pixel coords (already scaled by sc).
  // Returns [screenX, screenY] or null if behind camera.

  function proj(p) {
    const [x, y, z] = p;
    const zd = z + CAM_Z;
    if (zd < 0.5) return null;
    const f = FOCAL / zd;
    return [CX + x * f, CY - y * f];
  }

  /* ── Draw one blade ──────────────────────────────────────── */

  function drawBlade(pts, bT, lit) {
    const [q0, q1, q2, q3] = pts;
    if (!q0 || !q1 || !q2 || !q3) return;

    // Gradient axis: inner mid-edge → outer mid-edge
    const iMx = (q0[0] + q1[0]) * 0.5, iMy = (q0[1] + q1[1]) * 0.5;
    const oMx = (q2[0] + q3[0]) * 0.5, oMy = (q2[1] + q3[1]) * 0.5;

    const gr = ctx.createLinearGradient(iMx, iMy, oMx, oMy);

    // Hue cycles: deep violet (278°) → hot magenta-pink (330°) around the ring
    const hue = 278 + bT * 52;

    // Brightness: back blades get L≈0.25, front-lit blades get L≈1.0
    const L = 0.25 + 0.75 * lit;

    gr.addColorStop(0.00, `hsla(${hue},       98%, ${(8  * L).toFixed(0)}%, 0.98)`);
    gr.addColorStop(0.18, `hsla(${hue},       96%, ${(23 * L).toFixed(0)}%, 0.98)`);
    gr.addColorStop(0.44, `hsla(${hue + 10},  92%, ${(42 * L).toFixed(0)}%, 0.97)`);
    gr.addColorStop(0.66, `hsla(${hue + 20},  88%, ${(57 * L).toFixed(0)}%, 0.96)`);
    gr.addColorStop(0.82, `hsla(${hue + 30},  82%, ${(69 * L).toFixed(0)}%, 0.94)`);
    gr.addColorStop(0.92, `hsla(${hue + 38},  70%, ${(80 * L).toFixed(0)}%, 0.90)`);
    gr.addColorStop(1.00, `hsla(${hue + 46},  48%, 91%, 0.62)`);

    // Slightly curved sides via quadratic bezier — organic leaf shape
    const ba  = 0.06;
    const aDx = q2[0] - q1[0], aDy = q2[1] - q1[1];
    const bDx = q0[0] - q3[0], bDy = q0[1] - q3[1];
    const cpA = [(q1[0] + q2[0]) * 0.5 - aDy * ba, (q1[1] + q2[1]) * 0.5 + aDx * ba];
    const cpB = [(q3[0] + q0[0]) * 0.5 - bDy * ba, (q3[1] + q0[1]) * 0.5 + bDx * ba];

    ctx.beginPath();
    ctx.moveTo(q0[0], q0[1]);
    ctx.lineTo(q1[0], q1[1]);
    ctx.quadraticCurveTo(cpA[0], cpA[1], q2[0], q2[1]);
    ctx.lineTo(q3[0], q3[1]);
    ctx.quadraticCurveTo(cpB[0], cpB[1], q0[0], q0[1]);
    ctx.closePath();

    ctx.fillStyle = gr;
    ctx.fill();

    // Warm white-gold highlight stroke on the outer edge for bright blades
    if (lit > 0.35) {
      const ha = Math.min(0.84, (lit - 0.35) * 1.45);
      ctx.beginPath();
      ctx.moveTo(q3[0], q3[1]);
      ctx.quadraticCurveTo(cpA[0], cpA[1], q2[0], q2[1]);
      ctx.strokeStyle = `rgba(255, 228, 242, ${ha.toFixed(3)})`;
      ctx.lineWidth   = Math.max(0.35, lit * 1.7);
      ctx.stroke();
    }
  }

  /* ── Render torus ────────────────────────────────────────── */

  function renderTorus() {
    const rY = rotY + (smX - 0.5) * 0.30;
    const rX = BASE_RX + (0.5 - smY) * 0.20;

    // Build frame: rotate, project, compute lighting
    const frame = bladeBase.map(b => {
      // Scale to pixel space then apply global rotation
      const rc = b.c.map(c => rx3(ry3([c[0] * sc, c[1] * sc, c[2] * sc], rY), rX));
      const pts = rc.map(proj);

      // Average depth for painter's sort
      const avgZ = (rc[0][2] + rc[1][2] + rc[2][2] + rc[3][2]) * 0.25;

      // Rotate face normal, compute diffuse lighting
      const rn  = rx3(ry3(b.n, rY), rX);
      const lit = Math.max(0, rn[0] * LX + rn[1] * LY + rn[2] * LZ);

      return { pts, avgZ, lit, t: b.t };
    });

    // Back → front (painter's algorithm)
    frame.sort((a, b) => b.avgZ - a.avgZ);
    frame.forEach(d => drawBlade(d.pts, d.t, d.lit));
  }

  /* ── Orbital Scene Decor ──────────────────────────────────── */
  /*
   * Ring-and-particle field around the torus:
   *   - a faint starfield scattered across the whole scene
   *   - 2–3 thin elliptical guide rings around the torus
   *   - small glowing dots that revolve along those rings, at
   *     varying sizes / speeds / brightness (front half brighter,
   *     back half dimmed as it passes behind the torus)
   *   - a few fixed hexagon "sensor" badges placed around the scene
   *   - one small dashed link accent with two pulse nodes
   */

  // Rings: aU/bU = ellipse radii (design units), rot = tilt (radians)
  const RINGS = [
    { aU: 158, bU:  92, rot: -0.05, alpha: 0.30, dash: [] },
    { aU: 208, bU: 122, rot:  0.03, alpha: 0.22, dash: [] },
    { aU: 258, bU: 150, rot: -0.02, alpha: 0.15, dash: [2, 7] },
  ];

  // Particle colors — white / violet / blue / magenta
  const ORBIT_COLS = [
    [235, 232, 245],  // soft white
    [186, 156, 255],  // pale violet
    [139,  92, 246],  // violet-500
    [124,  58, 237],  // purple-600
    [ 99, 133, 255],  // periwinkle-blue
    [214, 110, 255],  // magenta
  ];

  let orbitParticles = [];
  let stars = [];
  let hexIcons = [];

  function buildOrbitParticles() {
    orbitParticles = [];
    RINGS.forEach((ring, ri) => {
      const count = 9 + ri * 4;
      for (let i = 0; i < count; i++) {
        const bright = Math.random() < 0.32;
        orbitParticles.push({
          ring: ri,
          phase: Math.random() * Math.PI * 2,
          speed: (0.06 + Math.random() * 0.10) * (Math.random() < 0.5 ? 1 : -1),
          size:  bright ? (1.8 + Math.random() * 1.6) : (0.8 + Math.random() * 1.1),
          bright,
          glow: bright && Math.random() < 0.55,
          col: ORBIT_COLS[Math.floor(Math.random() * ORBIT_COLS.length)],
          pulseF: 0.5 + Math.random() * 0.8,
          pulsePh: Math.random() * Math.PI * 2,
        });
      }
    });
  }

  function buildStarfield() {
    const count = Math.round((W * H) / 9000);
    stars = [];
    for (let i = 0; i < count; i++) {
      const bright = Math.random() < 0.08;
      stars.push({
        x: Math.random() * W,
        y: Math.random() * H,
        r: bright ? (0.9 + Math.random() * 0.8) : (0.4 + Math.random() * 0.5),
        a: bright ? (0.5 + Math.random() * 0.4) : (0.10 + Math.random() * 0.28),
        pulseF: 0.15 + Math.random() * 0.35,
        pulsePh: Math.random() * Math.PI * 2,
        tint: Math.random() < 0.25
          ? ORBIT_COLS[Math.floor(Math.random() * ORBIT_COLS.length)]
          : [235, 235, 245],
      });
    }
  }

  // Hex badges revolve together on their own ring (design units, offset from center)
  const HEX_RING = { aU: 300, bU: 178, rot: -0.03 };
  const HEX_SPEED = 0.045; // rad/sec — slow, deliberate revolution

  // Each badge gets its own accent color for variety, drawn from the same palette
  const HEX_DEFS = [
    { xU:  -6, yU: -170, icon: 'gear',   col: [186, 156, 255] },  // pale violet
    { xU: 210, yU:  -95, icon: 'shield', col: [214, 110, 255] },  // magenta
    { xU: 195, yU:  148, icon: 'wifi',   col: [120, 160, 255] },  // blue
    { xU: -95, yU:  190, icon: 'nodes',  col: [235, 232, 245] },  // soft white
    { xU: -232,yU:   28, icon: 'layers', col: [168, 110, 255] },  // purple
  ];

  function buildHexIcons() {
    hexIcons = HEX_DEFS.map(d => ({
      icon: d.icon,
      col: d.col,
      // Recover this badge's starting angle on HEX_RING from its old fixed offset
      phase: Math.atan2(d.yU / HEX_RING.bU, d.xU / HEX_RING.aU),
      pulsePh: Math.random() * Math.PI * 2,
    }));
  }

  function buildSceneDecor() {
    buildOrbitParticles();
    buildStarfield();
    buildHexIcons();
  }

  /* ── Starfield ────────────────────────────────────────────── */

  function drawStarfield(t) {
    stars.forEach(s => {
      const tw = 0.75 + 0.25 * Math.sin(t * s.pulseF + s.pulsePh);
      const a  = s.a * tw;
      const [cr, cg, cb] = s.tint;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${cr},${cg},${cb},${a.toFixed(3)})`;
      ctx.fill();
    });
  }

  /* ── Rings + orbiting particles ──────────────────────────── */

  function ringPoint(ring, theta) {
    const ex = ring.aU * Math.cos(theta);
    const ey = ring.bU * Math.sin(theta);
    const cr = Math.cos(ring.rot), sr = Math.sin(ring.rot);
    return {
      x: (ex * cr - ey * sr),
      y: (ex * sr + ey * cr),
      depth: ey, // >0 pseudo-front, <0 pseudo-back (pre-rotation vertical component)
    };
  }

  function drawRingLines() {
    RINGS.forEach(ring => {
      ctx.beginPath();
      for (let i = 0; i <= 96; i++) {
        const theta = (i / 96) * Math.PI * 2;
        const p = ringPoint(ring, theta);
        const sx = CX + p.x * sc, sy = CY + p.y * sc;
        if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
      }
      ctx.closePath();
      ctx.strokeStyle = `rgba(178, 140, 255, ${ring.alpha})`;
      ctx.lineWidth = 1;
      ctx.setLineDash(ring.dash);
      ctx.stroke();
      ctx.setLineDash([]);
    });
  }

  function drawOrbitParticles(t, frontHalf) {
    const mpx = (smX - 0.5) * 4;
    const mpy = (smY - 0.5) * 4;

    orbitParticles.forEach(p => {
      const ring = RINGS[p.ring];
      const theta = p.phase + t * p.speed;
      const pos = ringPoint(ring, theta);
      const isFront = pos.depth >= 0;
      if (isFront !== frontHalf) return;

      const depthF = 0.45 + 0.55 * (pos.depth / ring.bU); // 0(back)→1(front)
      const pulse  = 0.85 + 0.15 * Math.sin(t * p.pulseF + p.pulsePh);
      const alpha  = Math.max(0.08, (p.bright ? 0.95 : 0.58) * depthF * pulse);

      const sx = CX + pos.x * sc + mpx;
      const sy = CY + pos.y * sc + mpy;
      const rad = Math.max(0.6, p.size * sc * (0.65 + 0.35 * depthF));
      const [cr, cg, cb] = p.col;

      if (p.glow) {
        const gr = ctx.createRadialGradient(sx, sy, 0, sx, sy, rad * 4.2);
        gr.addColorStop(0, `rgba(${cr},${cg},${cb},${(alpha * 0.55).toFixed(3)})`);
        gr.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
        ctx.beginPath();
        ctx.arc(sx, sy, rad * 4.2, 0, Math.PI * 2);
        ctx.fillStyle = gr;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(sx, sy, rad, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${cr},${cg},${cb},${alpha.toFixed(3)})`;
      ctx.fill();
    });
  }

  /* ── Hexagon sensor badges ───────────────────────────────── */

  function hexPath(x, y, r) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i - Math.PI / 2;
      const px = x + r * Math.cos(a), py = y + r * Math.sin(a);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
  }

  function drawHexIcon(cx, cy, r, icon, glowA, depthF = 1, col = [186, 156, 255]) {
    const [cr, cg, cb] = col;

    // Soft ambient glow behind the whole badge
    const glowR = r * 2.6;
    const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, glowR);
    bg.addColorStop(0,   `rgba(${cr},${cg},${cb},${(0.28 + glowA * 0.20) * depthF})`);
    bg.addColorStop(0.6, `rgba(${cr},${cg},${cb},${0.10 * depthF})`);
    bg.addColorStop(1,   `rgba(${cr},${cg},${cb},0)`);
    ctx.beginPath();
    ctx.arc(cx, cy, glowR, 0, Math.PI * 2);
    ctx.fillStyle = bg;
    ctx.fill();

    // Tinted glass fill — subtle radial wash instead of flat dark
    hexPath(cx, cy, r);
    const fillGr = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    fillGr.addColorStop(0, `rgba(${cr},${cg},${cb},${0.26 * depthF})`);
    fillGr.addColorStop(1, `rgba(10, 6, 20, ${0.62 * depthF})`);
    ctx.fillStyle = fillGr;
    ctx.fill();

    // Bright outer edge + a faint outer echo for a "sensor ring" feel
    hexPath(cx, cy, r * 1.14);
    ctx.strokeStyle = `rgba(${cr},${cg},${cb},${(0.22 + glowA * 0.16) * depthF})`;
    ctx.lineWidth = 1;
    ctx.stroke();

    hexPath(cx, cy, r);
    ctx.strokeStyle = `rgba(${cr},${cg},${cb},${(0.72 + glowA * 0.28) * depthF})`;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Small glowing corner pips (top + bottom vertices) for a hi-tech accent
    [-Math.PI / 2, Math.PI / 2].forEach(a => {
      const px = cx + r * Math.cos(a), py = cy + r * Math.sin(a);
      ctx.beginPath();
      ctx.arc(px, py, Math.max(0.9, r * 0.05), 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${cr},${cg},${cb},${(0.7 + glowA * 0.3) * depthF})`;
      ctx.fill();
    });

    ctx.strokeStyle = `rgba(${Math.min(255, cr + 30)},${Math.min(255, cg + 25)},${Math.min(255, cb + 20)},${(0.75 + glowA * 0.25) * depthF})`;
    ctx.lineWidth = 1.3;
    ctx.lineCap = 'round';
    const s = r * 0.46;

    switch (icon) {
      case 'gear': {
        ctx.beginPath();
        ctx.arc(cx, cy, s * 0.55, 0, Math.PI * 2);
        ctx.stroke();
        for (let i = 0; i < 8; i++) {
          const a = (Math.PI / 4) * i;
          const x1 = cx + Math.cos(a) * s * 0.75, y1 = cy + Math.sin(a) * s * 0.75;
          const x2 = cx + Math.cos(a) * s * 1.05, y2 = cy + Math.sin(a) * s * 1.05;
          ctx.beginPath();
          ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
          ctx.stroke();
        }
        break;
      }
      case 'shield': {
        ctx.beginPath();
        ctx.moveTo(cx, cy - s);
        ctx.quadraticCurveTo(cx + s, cy - s * 0.7, cx + s, cy - s * 0.1);
        ctx.quadraticCurveTo(cx + s, cy + s * 0.8, cx, cy + s * 1.05);
        ctx.quadraticCurveTo(cx - s, cy + s * 0.8, cx - s, cy - s * 0.1);
        ctx.quadraticCurveTo(cx - s, cy - s * 0.7, cx, cy - s);
        ctx.closePath();
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(cx - s * 0.32, cy);
        ctx.lineTo(cx + s * 0.32, cy);
        ctx.moveTo(cx, cy - s * 0.32);
        ctx.lineTo(cx, cy + s * 0.32);
        ctx.stroke();
        break;
      }
      case 'wifi': {
        for (let i = 0; i < 3; i++) {
          ctx.beginPath();
          ctx.arc(cx, cy + s * 0.6, s * (0.35 + i * 0.35), -Math.PI * 0.78, -Math.PI * 0.22);
          ctx.stroke();
        }
        ctx.beginPath();
        ctx.arc(cx, cy + s * 0.6, s * 0.10, 0, Math.PI * 2);
        ctx.fillStyle = ctx.strokeStyle;
        ctx.fill();
        break;
      }
      case 'nodes': {
        const pts = [[-0.7, 0.5], [0, -0.65], [0.7, 0.5]];
        ctx.beginPath();
        ctx.moveTo(cx + pts[0][0] * s, cy + pts[0][1] * s);
        ctx.lineTo(cx + pts[1][0] * s, cy + pts[1][1] * s);
        ctx.lineTo(cx + pts[2][0] * s, cy + pts[2][1] * s);
        ctx.stroke();
        pts.forEach(([px, py]) => {
          ctx.beginPath();
          ctx.arc(cx + px * s, cy + py * s, s * 0.16, 0, Math.PI * 2);
          ctx.fillStyle = ctx.strokeStyle;
          ctx.fill();
        });
        break;
      }
      case 'layers': {
        [-0.35, 0, 0.35].forEach(oy => {
          ctx.beginPath();
          ctx.moveTo(cx - s * 0.9, cy + oy * s);
          ctx.lineTo(cx,           cy + oy * s - s * 0.28);
          ctx.lineTo(cx + s * 0.9, cy + oy * s);
          ctx.stroke();
        });
        break;
      }
    }
  }

  function drawHexIcons(t) {
    const baseR = Math.max(14, 20 * sc * 0.6);
    hexIcons.forEach(h => {
      const theta = h.phase + t * HEX_SPEED;
      const pos = ringPoint(HEX_RING, theta);
      const depthF = 0.62 + 0.38 * (pos.depth / HEX_RING.bU); // 0.24(back)→1(front)

      const cx = CX + pos.x * sc;
      const cy = CY + pos.y * sc;
      const r  = baseR * (0.82 + 0.18 * depthF);

      const glowA = (0.5 + 0.5 * Math.sin(t * 0.6 + h.pulsePh)) * depthF;
      drawHexIcon(cx, cy, r, h.icon, glowA, depthF, h.col);
    });
  }

  /* ── Link accent (dashed line + two pulse nodes) ─────────── */

  function drawLinkAccent(t) {
    const x1 = CX - 148 * sc, y1 = CY - 60 * sc;
    const x2 = CX - 78  * sc, y2 = CY - 10 * sc;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.setLineDash([3, 5]);
    ctx.strokeStyle = 'rgba(186, 156, 255, 0.30)';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.beginPath();
    ctx.arc(x1, y1, Math.max(1.5, 2 * sc * 0.5), 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(220, 205, 255, 0.55)';
    ctx.fill();

    const pulse = 0.5 + 0.5 * Math.sin(t * 1.4);
    ctx.beginPath();
    ctx.arc(x2, y2, Math.max(1.8, 2.4 * sc * 0.5), 0, Math.PI * 2);
    ctx.fillStyle = `rgba(214, 110, 255, ${0.55 + 0.35 * pulse})`;
    ctx.fill();
    const gr = ctx.createRadialGradient(x2, y2, 0, x2, y2, 10 * sc * 0.5);
    gr.addColorStop(0, `rgba(214, 110, 255, ${0.30 * pulse})`);
    gr.addColorStop(1, 'rgba(214, 110, 255, 0)');
    ctx.beginPath();
    ctx.arc(x2, y2, 10 * sc * 0.5, 0, Math.PI * 2);
    ctx.fillStyle = gr;
    ctx.fill();
  }

  /* ── Background glow ─────────────────────────────────────── */

  function drawGlow() {
    const r   = Math.min(W, H) * 0.54;
    const grd = ctx.createRadialGradient(CX, CY, 0, CX, CY, r);
    grd.addColorStop(0,    'rgba(96, 26, 190, 0.165)');
    grd.addColorStop(0.45, 'rgba(64, 12, 140, 0.085)');
    grd.addColorStop(1,    'rgba(0,0,0,0)');
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, W, H);
  }

  /* ── Animation loop ──────────────────────────────────────── */

  function frame(ts) {
    raf = requestAnimationFrame(frame);

    if (ts0 === null) ts0 = ts;
    const t = (ts - ts0) * 0.001;

    ctx.clearRect(0, 0, W, H);

    // Lerp mouse
    smX += (tgX - smX) * 0.055;
    smY += (tgY - smY) * 0.055;

    rotY += ROT_SPEED;

    drawStarfield(t);
    drawGlow();
    drawRingLines();
    drawOrbitParticles(t, false);  // back half — behind torus
    renderTorus();
    drawOrbitParticles(t, true);   // front half — in front of torus
    drawHexIcons(t);
    drawLinkAccent(t);
  }

  function staticFrame() {
    ctx.clearRect(0, 0, W, H);
    drawStarfield(0);
    drawGlow();
    drawRingLines();
    renderTorus();
    drawHexIcons(0);
  }

  /* ── Canvas sizing ───────────────────────────────────────── */

  function measure() {
    const rect = scene.getBoundingClientRect();
    W  = canvas.width  = Math.round(rect.width);
    H  = canvas.height = Math.round(rect.height);
    CX = W / 2;
    CY = H / 2;
    // sc: torus fills ~80-85% of the shorter dimension
    sc = Math.min(W, H) / 400;
  }

  function rebuild() {
    measure();
    buildSceneDecor();
  }

  /* ── Input ───────────────────────────────────────────────── */

  window.addEventListener('mousemove', e => {
    tgX = e.clientX / window.innerWidth;
    tgY = e.clientY / window.innerHeight;
  }, { passive: true });

  window.addEventListener('touchmove', e => {
    if (e.touches.length) {
      tgX = e.touches[0].clientX / window.innerWidth;
      tgY = e.touches[0].clientY / window.innerHeight;
    }
  }, { passive: true });

  /* ── Resize ──────────────────────────────────────────────── */

  let resizeTimer;

  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      cancelAnimationFrame(raf);
      ts0 = null;
      rebuild();
      if (RM) staticFrame();
      else raf = requestAnimationFrame(frame);
    }, 60);
  }

  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(onResize).observe(scene);
  } else {
    window.addEventListener('resize', onResize);
  }

  /* ── Entrance fade ───────────────────────────────────────── */

  const page = document.getElementById('page');
  if (page && !RM) {
    page.style.opacity = '0';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      page.style.transition = 'opacity 1.5s cubic-bezier(0.16,1,0.3,1)';
      page.style.opacity    = '1';
    }));
  }

  /* ── Boot ────────────────────────────────────────────────── */

  precomputeBlades();
  rebuild(); // calls measure + buildSceneDecor

  if (RM) staticFrame();
  else raf = requestAnimationFrame(frame);

})();
