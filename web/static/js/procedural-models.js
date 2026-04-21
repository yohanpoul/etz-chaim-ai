/**
 * procedural-models.js — Kabbalistic temple procedural objects
 *
 * Models missing from KayKit Dungeon that we need for the Etz Chaim world.
 * Each factory returns a THREE.Group ready to add to a scene.
 * Requires THREE to be loaded globally.
 */

// ═══════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════

function _mat(color, opts) {
    const o = Object.assign({ roughness: 0.6, metalness: 0.05 }, opts || {});
    return new THREE.MeshStandardMaterial({
        color: color,
        roughness: o.roughness,
        metalness: o.metalness,
        emissive: o.emissive || 0x000000,
        emissiveIntensity: o.emissiveIntensity || 0,
        transparent: o.transparent || false,
        opacity: o.opacity !== undefined ? o.opacity : 1.0,
        side: o.side || THREE.FrontSide
    });
}

function _mesh(geo, mat, pos, rot) {
    const m = new THREE.Mesh(geo, mat);
    if (pos) m.position.set(pos[0], pos[1], pos[2]);
    if (rot) m.rotation.set(rot[0], rot[1], rot[2]);
    m.castShadow = true;
    m.receiveShadow = true;
    return m;
}

// Lathe helper: rotate a 2D profile around Y axis
function _lathe(points, segments, mat, pos) {
    const vecs = points.map(p => new THREE.Vector2(p[0], p[1]));
    const geo = new THREE.LatheGeometry(vecs, segments || 16);
    return _mesh(geo, mat, pos);
}


// ═══════════════════════════════════════════════════════════════
//  1. MENORAH — 7-branch candelabrum
// ═══════════════════════════════════════════════════════════════

function createMenorah(opts) {
    const g = new THREE.Group();
    const gold = _mat(0xc9a020, { metalness: 0.7, roughness: 0.25 });
    const flame = _mat(0xffaa30, { emissive: 0xff8800, emissiveIntensity: 0.8 });

    // Base — three stacked discs
    g.add(_mesh(new THREE.CylinderGeometry(0.22, 0.25, 0.04, 16), gold, [0, 0.02, 0]));
    g.add(_mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.03, 16), gold, [0, 0.055, 0]));
    g.add(_mesh(new THREE.CylinderGeometry(0.14, 0.18, 0.03, 16), gold, [0, 0.085, 0]));

    // Central stem
    g.add(_mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.7, 8), gold, [0, 0.45, 0]));

    // Decorative knobs on stem
    [0.22, 0.38, 0.55].forEach(function(y) {
        g.add(_mesh(new THREE.SphereGeometry(0.035, 8, 8), gold, [0, y, 0]));
    });

    // Branch positions: 7 cups at different heights
    var branches = [
        { x: -0.30, h: 0.55 },
        { x: -0.20, h: 0.65 },
        { x: -0.10, h: 0.72 },
        { x:  0.00, h: 0.80 },  // center (tallest)
        { x:  0.10, h: 0.72 },
        { x:  0.20, h: 0.65 },
        { x:  0.30, h: 0.55 }
    ];

    branches.forEach(function(b) {
        // Curved arm from stem to cup position
        if (b.x !== 0) {
            var sign = b.x > 0 ? 1 : -1;
            var absX = Math.abs(b.x);

            // Horizontal portion from stem
            var hLen = absX * 0.6;
            g.add(_mesh(
                new THREE.CylinderGeometry(0.018, 0.018, hLen, 6),
                gold,
                [sign * hLen / 2, 0.35, 0],
                [0, 0, sign * Math.PI / 2]
            ));

            // Vertical portion up to cup
            var vLen = b.h - 0.35;
            g.add(_mesh(
                new THREE.CylinderGeometry(0.018, 0.018, vLen, 6),
                gold,
                [sign * hLen, 0.35 + vLen / 2, 0]
            ));

            // Diagonal connector
            var dLen = Math.sqrt((absX - hLen) * (absX - hLen) + 0.01);
            var dAngle = Math.atan2(absX - hLen, 0.1);
            g.add(_mesh(
                new THREE.CylinderGeometry(0.015, 0.015, dLen + 0.02, 6),
                gold,
                [sign * (hLen + (absX - hLen) / 2), 0.35 + vLen - 0.05, 0],
                [0, 0, sign * dAngle * 0.3]
            ));
        }

        // Cup (small cylinder)
        g.add(_mesh(
            new THREE.CylinderGeometry(0.03, 0.025, 0.04, 8),
            gold,
            [b.x, b.h, 0]
        ));

        // Flame (small elongated sphere)
        var flameGeo = new THREE.SphereGeometry(0.018, 6, 8);
        flameGeo.scale(1, 1.8, 1);
        g.add(_mesh(flameGeo, flame, [b.x, b.h + 0.05, 0]));
    });

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  2. TORAH SCROLL — open scroll on two rollers
// ═══════════════════════════════════════════════════════════════

function createTorahScroll(opts) {
    var g = new THREE.Group();
    var wood = _mat(0x8B6914, { roughness: 0.7 });
    var parchment = _mat(0xf5e6c8, { roughness: 0.9, metalness: 0 });
    var goldTip = _mat(0xc9a020, { metalness: 0.6, roughness: 0.3 });

    // Two roller poles (Atzei Chaim)
    [-0.18, 0.18].forEach(function(x) {
        // Main pole
        g.add(_mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.55, 8), wood, [x, 0.275, 0]));
        // Top finial (rimon)
        g.add(_mesh(new THREE.SphereGeometry(0.03, 8, 8), goldTip, [x, 0.56, 0]));
        g.add(_mesh(new THREE.CylinderGeometry(0.015, 0.025, 0.02, 8), goldTip, [x, 0.53, 0]));
        // Bottom knob
        g.add(_mesh(new THREE.SphereGeometry(0.025, 8, 8), wood, [x, 0.02, 0]));
        // Handle discs
        g.add(_mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.015, 8), wood, [x, 0.08, 0]));
        g.add(_mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.015, 8), wood, [x, 0.46, 0]));
    });

    // Rolled portions on each side
    [-0.18, 0.18].forEach(function(x) {
        g.add(_mesh(
            new THREE.CylinderGeometry(0.045, 0.045, 0.38, 12),
            parchment,
            [x, 0.27, 0]
        ));
    });

    // Open parchment sheet between rollers
    var sheetGeo = new THREE.PlaneGeometry(0.28, 0.38, 8, 1);
    // Slight curve in the sheet
    var positions = sheetGeo.attributes.position;
    for (var i = 0; i < positions.count; i++) {
        var px = positions.getX(i);
        positions.setZ(i, Math.pow(px / 0.14, 2) * 0.015);
    }
    positions.needsUpdate = true;
    sheetGeo.computeVertexNormals();

    var sheet = _mesh(sheetGeo, parchment, [0, 0.27, 0.03]);
    sheet.material = _mat(0xf0ddb8, { roughness: 0.95, side: THREE.DoubleSide });
    g.add(sheet);

    // Text lines on parchment (thin dark strips)
    var ink = _mat(0x1a1008, { roughness: 0.9 });
    for (var row = 0; row < 12; row++) {
        var y = 0.42 - row * 0.028;
        var lineW = 0.18 + Math.random() * 0.06;
        g.add(_mesh(
            new THREE.BoxGeometry(lineW, 0.004, 0.001),
            ink,
            [0, y, 0.042]
        ));
    }

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  3. BOOK STACK — pile of thick leather-bound tomes
// ═══════════════════════════════════════════════════════════════

function createBookStack(opts) {
    var g = new THREE.Group();

    var books = [
        { w: 0.22, h: 0.04, d: 0.16, color: 0x6b1a1a, y: 0.02 },   // dark red
        { w: 0.20, h: 0.035, d: 0.15, color: 0x1a3a6b, y: 0.058 },  // blue
        { w: 0.24, h: 0.045, d: 0.17, color: 0x2a1a0a, y: 0.098 },  // brown
        { w: 0.19, h: 0.03, d: 0.14, color: 0x1a4a1a, y: 0.136 },   // green
        { w: 0.21, h: 0.04, d: 0.16, color: 0x4a1a4a, y: 0.171 }    // purple
    ];

    var pageMat = _mat(0xf0e8d0, { roughness: 0.95 });

    books.forEach(function(b, idx) {
        var cover = _mat(b.color, { roughness: 0.8, metalness: 0.05 });

        // Book body
        var body = _mesh(
            new THREE.BoxGeometry(b.w, b.h, b.d),
            cover,
            [0, b.y, 0]
        );
        // Slight random rotation for natural look
        body.rotation.y = (Math.random() - 0.5) * 0.15;
        g.add(body);

        // Page edges visible (inset lighter strip)
        var pages = _mesh(
            new THREE.BoxGeometry(b.w - 0.01, b.h - 0.008, b.d - 0.015),
            pageMat,
            [0.003, b.y, 0.004]
        );
        pages.rotation.y = body.rotation.y;
        g.add(pages);

        // Spine ridge
        var spine = _mesh(
            new THREE.BoxGeometry(0.005, b.h + 0.002, b.d - 0.01),
            _mat(b.color * 0.8 | 0, { metalness: 0.1 }),
            [-b.w / 2 + 0.003, b.y, 0]
        );
        spine.rotation.y = body.rotation.y;
        g.add(spine);
    });

    // Top book slightly askew with gold title emboss
    var topGold = _mesh(
        new THREE.BoxGeometry(0.08, 0.003, 0.005),
        _mat(0xc9a020, { metalness: 0.5 }),
        [0, 0.195, 0]
    );
    g.add(topGold);

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  4. OPEN BOOK — single book lying open
// ═══════════════════════════════════════════════════════════════

function createOpenBook(opts) {
    var g = new THREE.Group();
    var coverColor = (opts && opts.color) || 0x6b1a1a;
    var cover = _mat(coverColor, { roughness: 0.8 });
    var page = _mat(0xf5edd8, { roughness: 0.95, side: THREE.DoubleSide });
    var ink = _mat(0x1a1008, { roughness: 0.9 });

    // Left cover (angled open)
    var leftCover = _mesh(
        new THREE.BoxGeometry(0.14, 0.008, 0.20),
        cover,
        [-0.075, 0.008, 0]
    );
    leftCover.rotation.z = 0.08;
    g.add(leftCover);

    // Right cover (angled open)
    var rightCover = _mesh(
        new THREE.BoxGeometry(0.14, 0.008, 0.20),
        cover,
        [0.075, 0.008, 0]
    );
    rightCover.rotation.z = -0.08;
    g.add(rightCover);

    // Spine
    g.add(_mesh(
        new THREE.BoxGeometry(0.015, 0.025, 0.20),
        cover,
        [0, 0.012, 0]
    ));

    // Left page spread
    var leftPage = _mesh(
        new THREE.PlaneGeometry(0.12, 0.18),
        page,
        [-0.065, 0.018, 0],
        [-Math.PI / 2, 0, 0.04]
    );
    g.add(leftPage);

    // Right page spread
    var rightPage = _mesh(
        new THREE.PlaneGeometry(0.12, 0.18),
        page,
        [0.065, 0.018, 0],
        [-Math.PI / 2, 0, -0.04]
    );
    g.add(rightPage);

    // Text lines on pages
    for (var side = -1; side <= 1; side += 2) {
        for (var row = 0; row < 10; row++) {
            var lineW = 0.06 + Math.random() * 0.04;
            g.add(_mesh(
                new THREE.BoxGeometry(lineW, 0.001, 0.003),
                ink,
                [side * 0.065, 0.019, -0.07 + row * 0.016]
            ));
        }
    }

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  5. TELESCOPE — brass tube on wooden tripod
// ═══════════════════════════════════════════════════════════════

function createTelescope(opts) {
    var g = new THREE.Group();
    var brass = _mat(0xb08830, { metalness: 0.6, roughness: 0.3 });
    var darkBrass = _mat(0x806020, { metalness: 0.5, roughness: 0.35 });
    var wood = _mat(0x6b4420, { roughness: 0.8 });
    var lens = _mat(0x4466aa, {
        metalness: 0.2, roughness: 0.1,
        transparent: true, opacity: 0.5
    });

    // Main tube (tapered)
    g.add(_mesh(
        new THREE.CylinderGeometry(0.035, 0.045, 0.50, 12),
        brass,
        [0, 0.52, 0],
        [0, 0, 0.35]
    ));

    // Tube rings (decorative bands)
    [0.38, 0.50, 0.62].forEach(function(t) {
        var py = 0.52 + Math.sin(0.35) * (t - 0.50);
        var px = Math.cos(0.35) * (t - 0.50) * 0.1;
        g.add(_mesh(
            new THREE.TorusGeometry(0.042, 0.005, 8, 12),
            darkBrass,
            [px * 0.3, 0.52 + (t - 0.50) * 0.15, 0],
            [Math.PI / 2 - 0.35, 0, 0]
        ));
    });

    // Eyepiece (smaller cylinder at back)
    g.add(_mesh(
        new THREE.CylinderGeometry(0.025, 0.03, 0.08, 10),
        darkBrass,
        [-0.09, 0.46, 0],
        [0, 0, 0.35]
    ));

    // Lens at front (disc)
    g.add(_mesh(
        new THREE.CylinderGeometry(0.042, 0.042, 0.005, 12),
        lens,
        [0.09, 0.58, 0],
        [0, 0, 0.35]
    ));

    // Lens rim
    g.add(_mesh(
        new THREE.TorusGeometry(0.044, 0.004, 8, 16),
        darkBrass,
        [0.09, 0.58, 0],
        [Math.PI / 2 - 0.35, 0, 0]
    ));

    // Tripod pivot (central hub)
    g.add(_mesh(
        new THREE.SphereGeometry(0.03, 8, 8),
        brass,
        [0, 0.40, 0]
    ));

    // Three tripod legs
    for (var i = 0; i < 3; i++) {
        var angle = (i * Math.PI * 2) / 3 - Math.PI / 6;
        var legLen = 0.45;
        var legX = Math.cos(angle) * 0.17;
        var legZ = Math.sin(angle) * 0.17;

        // Upper leg
        var leg = _mesh(
            new THREE.CylinderGeometry(0.012, 0.015, legLen, 6),
            wood,
            [legX / 2, 0.20, legZ / 2]
        );
        leg.rotation.z = Math.atan2(legX, legLen) * 1.2;
        leg.rotation.x = -Math.atan2(legZ, legLen) * 1.2;
        g.add(leg);

        // Foot (small flat disc)
        g.add(_mesh(
            new THREE.CylinderGeometry(0.018, 0.02, 0.008, 8),
            wood,
            [legX, 0.004, legZ]
        ));
    }

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  6. BALANCE / SCALES — Moznayim (Gevurah symbol)
// ═══════════════════════════════════════════════════════════════

function createBalance(opts) {
    var g = new THREE.Group();
    var gold = _mat(0xc9a020, { metalness: 0.65, roughness: 0.25 });
    var darkGold = _mat(0x907018, { metalness: 0.6, roughness: 0.3 });

    // Central pillar
    g.add(_mesh(new THREE.CylinderGeometry(0.025, 0.035, 0.50, 8), gold, [0, 0.25, 0]));

    // Base — hexagonal
    g.add(_mesh(new THREE.CylinderGeometry(0.18, 0.20, 0.03, 6), darkGold, [0, 0.015, 0]));
    g.add(_mesh(new THREE.CylinderGeometry(0.14, 0.18, 0.02, 6), gold, [0, 0.04, 0]));

    // Top ornament (finial)
    g.add(_mesh(new THREE.SphereGeometry(0.025, 8, 8), gold, [0, 0.52, 0]));
    g.add(_mesh(new THREE.ConeGeometry(0.02, 0.03, 8), gold, [0, 0.555, 0]));

    // Horizontal beam
    var beam = _mesh(
        new THREE.BoxGeometry(0.50, 0.015, 0.015),
        gold,
        [0, 0.49, 0]
    );
    // Slight tilt for visual interest
    beam.rotation.z = 0.04;
    g.add(beam);

    // Two pans with chains
    [-0.22, 0.22].forEach(function(x) {
        var tilt = x < 0 ? 0.04 : -0.04;
        var panY = 0.28 + (x < 0 ? 0.01 : -0.01);

        // Pan (shallow bowl shape via lathe)
        var panProfile = [
            [0, 0], [0.07, 0.005], [0.08, 0.015], [0.075, 0.025], [0.065, 0.028]
        ];
        var pan = _lathe(panProfile, 16, darkGold, [x, panY, 0]);
        g.add(pan);

        // Three chains (thin cylinders from beam to pan edge)
        for (var c = 0; c < 3; c++) {
            var ca = (c * Math.PI * 2) / 3;
            var cx = x + Math.cos(ca) * 0.05;
            var cz = Math.sin(ca) * 0.05;
            var chainH = 0.49 + tilt * (x / 0.22) - panY - 0.02;

            // Chain links (series of small toruses)
            var links = 5;
            for (var lk = 0; lk < links; lk++) {
                var ly = panY + 0.03 + (chainH * lk) / links;
                g.add(_mesh(
                    new THREE.TorusGeometry(0.006, 0.0015, 4, 6),
                    gold,
                    [cx, ly, cz],
                    [lk % 2 === 0 ? 0 : Math.PI / 2, 0, 0]
                ));
            }
        }
    });

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  7. MIRROR — ornate standing mirror (Da'at)
// ═══════════════════════════════════════════════════════════════

function createMirror(opts) {
    var g = new THREE.Group();
    var frame = _mat(0x806030, { metalness: 0.3, roughness: 0.5 });
    var goldAccent = _mat(0xc9a020, { metalness: 0.6, roughness: 0.3 });
    var glass = _mat(0xaabbcc, {
        metalness: 0.95, roughness: 0.05,
        transparent: true, opacity: 0.85
    });

    // Stand legs (two angled supports)
    [-0.12, 0.12].forEach(function(x) {
        g.add(_mesh(
            new THREE.CylinderGeometry(0.018, 0.022, 0.5, 6),
            frame,
            [x, 0.25, 0.04],
            [0.12, 0, x > 0 ? -0.08 : 0.08]
        ));
        // Foot
        g.add(_mesh(
            new THREE.BoxGeometry(0.06, 0.015, 0.08),
            frame,
            [x * 1.1, 0.008, 0.08]
        ));
    });

    // Cross brace
    g.add(_mesh(
        new THREE.CylinderGeometry(0.01, 0.01, 0.22, 6),
        frame,
        [0, 0.18, 0.05],
        [0, 0, Math.PI / 2]
    ));

    // Mirror frame — oval shape (torus squished)
    var frameShape = new THREE.Shape();
    var fw = 0.18, fh = 0.28;
    frameShape.ellipse(0, 0, fw, fh, 0, Math.PI * 2, false, 0);
    var hole = new THREE.Path();
    hole.ellipse(0, 0, fw - 0.02, fh - 0.02, 0, Math.PI * 2, false, 0);
    frameShape.holes.push(hole);

    var frameGeo = new THREE.ExtrudeGeometry(frameShape, {
        depth: 0.02, bevelEnabled: true,
        bevelThickness: 0.005, bevelSize: 0.005, bevelSegments: 2
    });
    var frameMesh = _mesh(frameGeo, goldAccent, [0, 0.55, 0]);
    frameMesh.rotation.x = 0.08;
    g.add(frameMesh);

    // Mirror glass (oval disc)
    var glassShape = new THREE.Shape();
    glassShape.ellipse(0, 0, fw - 0.02, fh - 0.02, 0, Math.PI * 2, false, 0);
    var glassGeo = new THREE.ShapeGeometry(glassShape, 24);
    var glassMesh = _mesh(glassGeo, glass, [0, 0.55, 0.01]);
    glassMesh.rotation.x = 0.08;
    g.add(glassMesh);

    // Top ornament (finial)
    g.add(_mesh(
        new THREE.SphereGeometry(0.025, 8, 8),
        goldAccent,
        [0, 0.84, -0.01]
    ));
    // Small crown shape on top
    for (var p = 0; p < 5; p++) {
        var pa = (p / 5) * Math.PI - Math.PI / 2;
        g.add(_mesh(
            new THREE.ConeGeometry(0.008, 0.025, 4),
            goldAccent,
            [Math.cos(pa) * 0.02, 0.87, Math.sin(pa) * 0.015 - 0.01]
        ));
    }

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  8. THRONE — ornate high-back chair
// ═══════════════════════════════════════════════════════════════

function createThrone(opts) {
    var g = new THREE.Group();
    var wood = _mat(0x4a2810, { roughness: 0.7, metalness: 0.05 });
    var cushion = _mat((opts && opts.cushionColor) || 0x6b1040, { roughness: 0.85 });
    var gold = _mat(0xc9a020, { metalness: 0.6, roughness: 0.3 });

    // Four legs (turned, thicker)
    [[-0.18, -0.16], [0.18, -0.16], [-0.18, 0.16], [0.18, 0.16]].forEach(function(pos) {
        // Main leg
        g.add(_mesh(
            new THREE.CylinderGeometry(0.03, 0.035, 0.35, 8),
            wood,
            [pos[0], 0.175, pos[1]]
        ));
        // Decorative ring
        g.add(_mesh(
            new THREE.TorusGeometry(0.035, 0.006, 6, 8),
            gold,
            [pos[0], 0.12, pos[1]],
            [Math.PI / 2, 0, 0]
        ));
        // Ball foot
        g.add(_mesh(
            new THREE.SphereGeometry(0.03, 8, 6),
            gold,
            [pos[0], 0.01, pos[1]]
        ));
    });

    // Seat frame
    g.add(_mesh(
        new THREE.BoxGeometry(0.44, 0.04, 0.38),
        wood,
        [0, 0.37, 0]
    ));

    // Seat cushion
    var cushGeo = new THREE.BoxGeometry(0.38, 0.05, 0.32);
    // Round the top edges
    g.add(_mesh(cushGeo, cushion, [0, 0.415, 0]));

    // Armrests
    [-0.22, 0.22].forEach(function(x) {
        // Vertical support
        g.add(_mesh(
            new THREE.BoxGeometry(0.04, 0.22, 0.04),
            wood,
            [x, 0.50, -0.14]
        ));
        // Arm top (horizontal)
        g.add(_mesh(
            new THREE.BoxGeometry(0.05, 0.03, 0.30),
            wood,
            [x, 0.60, 0.0]
        ));
        // Arm end knob
        g.add(_mesh(
            new THREE.SphereGeometry(0.025, 8, 8),
            gold,
            [x, 0.62, 0.15]
        ));
    });

    // Tall back
    g.add(_mesh(
        new THREE.BoxGeometry(0.44, 0.65, 0.035),
        wood,
        [0, 0.72, -0.17]
    ));

    // Back cushion/padding (inset)
    g.add(_mesh(
        new THREE.BoxGeometry(0.36, 0.50, 0.02),
        cushion,
        [0, 0.68, -0.155]
    ));

    // Crown/crest on top of back
    // Central peak
    g.add(_mesh(
        new THREE.ConeGeometry(0.04, 0.10, 6),
        gold,
        [0, 1.10, -0.17]
    ));
    // Side peaks
    [-0.10, 0.10].forEach(function(x) {
        g.add(_mesh(
            new THREE.ConeGeometry(0.025, 0.06, 6),
            gold,
            [x, 1.08, -0.17]
        ));
    });
    // Crown base bar
    g.add(_mesh(
        new THREE.BoxGeometry(0.35, 0.03, 0.04),
        gold,
        [0, 1.04, -0.17]
    ));

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  9. ALTAR — stone altar table with engraved symbols
// ═══════════════════════════════════════════════════════════════

function createAltar(opts) {
    var g = new THREE.Group();
    var stone = _mat(0x8a8078, { roughness: 0.9, metalness: 0.02 });
    var darkStone = _mat(0x605850, { roughness: 0.85, metalness: 0.05 });
    var gold = _mat(0xc9a020, { metalness: 0.5, roughness: 0.3 });

    // Base platform
    g.add(_mesh(new THREE.BoxGeometry(0.70, 0.05, 0.45), darkStone, [0, 0.025, 0]));

    // Four corner pillars
    [[-0.28, -0.16], [0.28, -0.16], [-0.28, 0.16], [0.28, 0.16]].forEach(function(pos) {
        g.add(_mesh(
            new THREE.CylinderGeometry(0.04, 0.05, 0.45, 8),
            stone,
            [pos[0], 0.275, pos[1]]
        ));
        // Capital
        g.add(_mesh(
            new THREE.CylinderGeometry(0.055, 0.04, 0.03, 8),
            stone,
            [pos[0], 0.50, pos[1]]
        ));
    });

    // Top slab
    g.add(_mesh(new THREE.BoxGeometry(0.72, 0.04, 0.48), stone, [0, 0.52, 0]));

    // Decorative inset on top (gold line border)
    g.add(_mesh(
        new THREE.BoxGeometry(0.58, 0.005, 0.005),
        gold,
        [0, 0.545, -0.17]
    ));
    g.add(_mesh(
        new THREE.BoxGeometry(0.58, 0.005, 0.005),
        gold,
        [0, 0.545, 0.17]
    ));
    g.add(_mesh(
        new THREE.BoxGeometry(0.005, 0.005, 0.34),
        gold,
        [-0.29, 0.545, 0]
    ));
    g.add(_mesh(
        new THREE.BoxGeometry(0.005, 0.005, 0.34),
        gold,
        [0.29, 0.545, 0]
    ));

    // Central symbol — Star of David (two overlapping triangles)
    var tri1 = new THREE.Shape();
    var r = 0.06;
    for (var i = 0; i < 3; i++) {
        var a = (i * Math.PI * 2) / 3 - Math.PI / 2;
        if (i === 0) tri1.moveTo(Math.cos(a) * r, Math.sin(a) * r);
        else tri1.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    tri1.closePath();
    var triGeo1 = new THREE.ShapeGeometry(tri1);
    var s1 = _mesh(triGeo1, gold, [0, 0.546, 0], [-Math.PI / 2, 0, 0]);
    g.add(s1);

    var tri2 = new THREE.Shape();
    for (var j = 0; j < 3; j++) {
        var b = (j * Math.PI * 2) / 3 + Math.PI / 2;
        if (j === 0) tri2.moveTo(Math.cos(b) * r, Math.sin(b) * r);
        else tri2.lineTo(Math.cos(b) * r, Math.sin(b) * r);
    }
    tri2.closePath();
    var triGeo2 = new THREE.ShapeGeometry(tri2);
    var s2 = _mesh(triGeo2, gold, [0, 0.547, 0], [-Math.PI / 2, 0, 0]);
    g.add(s2);

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  10. INCENSE BURNER — Ketoret vessel
// ═══════════════════════════════════════════════════════════════

function createIncenseBurner(opts) {
    var g = new THREE.Group();
    var bronze = _mat(0x8a6830, { metalness: 0.55, roughness: 0.35 });
    var darkBronze = _mat(0x6a4820, { metalness: 0.5, roughness: 0.4 });

    // Base
    g.add(_mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.02, 8), bronze, [0, 0.01, 0]));

    // Stem
    g.add(_mesh(new THREE.CylinderGeometry(0.015, 0.02, 0.10, 8), bronze, [0, 0.07, 0]));

    // Bowl — lathe profile (wide bowl shape)
    var bowlProfile = [
        [0.00, 0.00],
        [0.06, 0.01],
        [0.08, 0.04],
        [0.07, 0.08],
        [0.06, 0.10],
        [0.055, 0.105]
    ];
    g.add(_lathe(bowlProfile, 12, darkBronze, [0, 0.12, 0]));

    // Smoke wisps (thin translucent cones rising up)
    var smokeMat = _mat(0xcccccc, {
        transparent: true, opacity: 0.15,
        side: THREE.DoubleSide
    });
    for (var s = 0; s < 3; s++) {
        var sx = (Math.random() - 0.5) * 0.03;
        var sz = (Math.random() - 0.5) * 0.03;
        g.add(_mesh(
            new THREE.ConeGeometry(0.015, 0.15 + Math.random() * 0.1, 5),
            smokeMat,
            [sx, 0.32 + s * 0.05, sz],
            [0, Math.random() * Math.PI, (Math.random() - 0.5) * 0.2]
        ));
    }

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  11. CRYSTAL ORB — glowing sphere on a stand
// ═══════════════════════════════════════════════════════════════

function createCrystalOrb(opts) {
    var g = new THREE.Group();
    var orbColor = (opts && opts.color) || 0x88aaff;
    var base = _mat(0x404040, { metalness: 0.4, roughness: 0.4 });
    var gold = _mat(0xc9a020, { metalness: 0.6, roughness: 0.3 });
    var crystal = _mat(orbColor, {
        metalness: 0.1, roughness: 0.05,
        transparent: true, opacity: 0.7,
        emissive: orbColor, emissiveIntensity: 0.2
    });

    // Base ring
    g.add(_mesh(new THREE.TorusGeometry(0.06, 0.012, 8, 16), base, [0, 0.06, 0], [Math.PI / 2, 0, 0]));

    // Three curved claws holding the orb
    for (var i = 0; i < 3; i++) {
        var a = (i * Math.PI * 2) / 3;
        var cx = Math.cos(a) * 0.05;
        var cz = Math.sin(a) * 0.05;
        g.add(_mesh(
            new THREE.CylinderGeometry(0.008, 0.012, 0.08, 6),
            gold,
            [cx, 0.08, cz],
            [0, 0, -Math.atan2(cx, 0.08)]
        ));
        // Claw tip curving inward
        g.add(_mesh(
            new THREE.SphereGeometry(0.008, 6, 6),
            gold,
            [cx * 0.7, 0.12, cz * 0.7]
        ));
    }

    // The orb itself
    g.add(_mesh(new THREE.SphereGeometry(0.06, 20, 20), crystal, [0, 0.14, 0]));

    // Inner glow core (smaller, brighter)
    var core = _mat(orbColor, {
        emissive: orbColor, emissiveIntensity: 0.6,
        transparent: true, opacity: 0.4
    });
    g.add(_mesh(new THREE.SphereGeometry(0.03, 12, 12), core, [0, 0.14, 0]));

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  12. SCROLL RACK — wooden frame holding multiple scrolls
// ═══════════════════════════════════════════════════════════════

function createScrollRack(opts) {
    var g = new THREE.Group();
    var wood = _mat(0x6b4420, { roughness: 0.8 });
    var parchment = _mat(0xf0ddb8, { roughness: 0.9 });
    var ribbon = [0x8b1a1a, 0x1a3a8b, 0x2a6b2a, 0x6b4a1a];

    // Frame uprights
    [-0.20, 0.20].forEach(function(x) {
        g.add(_mesh(
            new THREE.BoxGeometry(0.03, 0.50, 0.04),
            wood,
            [x, 0.25, 0]
        ));
    });

    // Shelves (3 levels)
    [0.05, 0.20, 0.35].forEach(function(y) {
        g.add(_mesh(
            new THREE.BoxGeometry(0.42, 0.015, 0.10),
            wood,
            [0, y, 0]
        ));
    });

    // Top piece
    g.add(_mesh(
        new THREE.BoxGeometry(0.46, 0.02, 0.06),
        wood,
        [0, 0.51, 0]
    ));

    // Scrolls on each shelf (rolled cylinders)
    [0.07, 0.22, 0.37].forEach(function(y, shelf) {
        var count = 3 + Math.floor(Math.random() * 2);
        for (var s = 0; s < count; s++) {
            var sx = -0.13 + s * 0.075 + (Math.random() - 0.5) * 0.02;
            var scrollR = 0.018 + Math.random() * 0.008;
            g.add(_mesh(
                new THREE.CylinderGeometry(scrollR, scrollR, 0.08, 8),
                parchment,
                [sx, y + scrollR + 0.015, 0],
                [0, 0, (Math.random() - 0.5) * 0.1]
            ));
            // Ribbon tie
            g.add(_mesh(
                new THREE.TorusGeometry(scrollR + 0.003, 0.003, 4, 8),
                _mat(ribbon[s % ribbon.length]),
                [sx, y + scrollR + 0.015, 0],
                [0, 0, Math.PI / 2]
            ));
        }
    });

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  13. ANVIL — forge anvil (Gevurah)
// ═══════════════════════════════════════════════════════════════

function createAnvil(opts) {
    var g = new THREE.Group();
    var iron = _mat(0x4a4a4a, { metalness: 0.7, roughness: 0.3 });
    var darkIron = _mat(0x353535, { metalness: 0.65, roughness: 0.35 });

    // Base block (wooden stump)
    var stump = _mat(0x5a3a1a, { roughness: 0.85 });
    g.add(_mesh(new THREE.CylinderGeometry(0.14, 0.16, 0.20, 8), stump, [0, 0.10, 0]));

    // Anvil body (wide base)
    g.add(_mesh(
        new THREE.BoxGeometry(0.22, 0.10, 0.12),
        iron,
        [0, 0.25, 0]
    ));

    // Waist (narrower middle)
    g.add(_mesh(
        new THREE.BoxGeometry(0.16, 0.06, 0.10),
        darkIron,
        [0, 0.33, 0]
    ));

    // Face (wide flat top)
    g.add(_mesh(
        new THREE.BoxGeometry(0.24, 0.03, 0.13),
        iron,
        [0, 0.375, 0]
    ));

    // Horn (tapered end)
    g.add(_mesh(
        new THREE.CylinderGeometry(0.01, 0.04, 0.14, 8),
        iron,
        [0.17, 0.37, 0],
        [0, 0, -Math.PI / 2 + 0.15]
    ));

    // Heel (flat back end)
    g.add(_mesh(
        new THREE.BoxGeometry(0.06, 0.05, 0.12),
        darkIron,
        [-0.14, 0.36, 0]
    ));

    // Hardy hole (small square indent on top)
    g.add(_mesh(
        new THREE.BoxGeometry(0.015, 0.01, 0.015),
        _mat(0x1a1a1a),
        [0.05, 0.395, 0]
    ));

    return g;
}


// ═══════════════════════════════════════════════════════════════
//  EXPORTS — attach all factories to window.ProceduralModels
// ═══════════════════════════════════════════════════════════════

window.ProceduralModels = {
    createMenorah: createMenorah,
    createTorahScroll: createTorahScroll,
    createBookStack: createBookStack,
    createOpenBook: createOpenBook,
    createTelescope: createTelescope,
    createBalance: createBalance,
    createMirror: createMirror,
    createThrone: createThrone,
    createAltar: createAltar,
    createIncenseBurner: createIncenseBurner,
    createCrystalOrb: createCrystalOrb,
    createScrollRack: createScrollRack,
    createAnvil: createAnvil
};
