from pd import ENERGY, np


def energy(velocity):
    return 0.5 * np.mean(np.sum(velocity * velocity, axis=0))


def solenoidal(flow, velocity):
    return flow.physical(flow.project(flow.transform(velocity)))


def random_phases(flow, rng, k0, shape):
    k = np.sqrt(flow.k2)
    spectrum = k ** 4 * np.exp(-2 * (k / k0) ** 2)
    amplitude = np.sqrt(spectrum * flow.inverse_k2)
    return amplitude * np.exp(1j * rng.uniform(0, 2 * np.pi, size=shape))


def random_field(flow, seed, k0):
    rng = np.random.default_rng(seed)
    velocity = solenoidal(flow, flow.physical(random_phases(flow, rng, k0, flow.k.shape)))
    return velocity * np.sqrt(ENERGY / energy(velocity))


def taylor_green(flow):
    velocity = solenoidal(flow, flow.initial())
    return velocity * np.sqrt(ENERGY / energy(velocity))


def initial_state(flow, name, k0):
    return taylor_green(flow) if name == "tg" else random_field(flow, int(name), k0)
