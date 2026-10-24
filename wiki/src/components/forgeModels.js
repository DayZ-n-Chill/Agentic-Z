// Models for the home card's forge (HeroForge.jsx). Each is Brian's own model, made in Meshy,
// converted into two parts (forgeZombie.json): `wire`, a simplified mesh the agents build edge by
// edge (points already centred, scaled to a unit sphere and turned to face the viewer; edges
// listed with the faces they border, bottom up), and `render`, a denser vertex-coloured mesh the
// hero shows solid once the wireframe is finished.
import ZOMBIE from './forgeZombie.json';

const fromMeshy = (data) => ({
  ...data.wire,
  e: data.wire.e.map(([a, b, f]) => ({ a, b, f })),
  two: data.wire.fn.map(() => false),
  render: data.render,
});

export const MODELS = [fromMeshy(ZOMBIE)];
