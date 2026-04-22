from bot import Bot


class FakeEnv:
    def __init__(self):
        self.attacking = False
        self.has_target = False
        self.actions = []
        self.sleeps = []
        self.markers = [(100, 200), (300, 400)]
        self._marker_choice_idx = 0

    def is_attacking(self):
        return self.attacking

    def has_target_in_battle_list(self):
        return self.has_target

    def press_space(self):
        self.actions.append(("space",))

    def loot(self):
        self.actions.append(("loot",))

    def click(self, x, y):
        self.actions.append(("click", x, y))

    def sleep(self, s):
        self.sleeps.append(s)

    def choose_marker(self, markers):
        m = markers[self._marker_choice_idx % len(markers)]
        self._marker_choice_idx += 1
        return m

    def walk_delay(self):
        return 2.0

    def find_markers(self):
        return list(self.markers)


def make_bot(env):
    return Bot(
        is_attacking=env.is_attacking,
        has_target=env.has_target_in_battle_list,
        press_space=env.press_space,
        loot=env.loot,
        click=env.click,
        sleep=env.sleep,
        choose_marker=env.choose_marker,
        walk_delay=env.walk_delay,
        find_markers=env.find_markers,
    )


def test_tick_presses_space_when_target_present():
    env = FakeEnv()
    env.has_target = True
    bot = make_bot(env)
    bot.tick()
    assert ("space",) in env.actions


def test_tick_waits_when_already_attacking():
    env = FakeEnv()
    env.attacking = True
    bot = make_bot(env)
    bot.tick()
    assert env.actions == []
    assert bot.was_attacking is True


def test_tick_loots_after_kill():
    env = FakeEnv()
    bot = make_bot(env)
    env.attacking = True
    bot.tick()
    env.attacking = False
    env.has_target = False
    bot.tick()
    assert ("loot",) in env.actions
    assert bot.was_attacking is False


def test_tick_attacks_next_target_immediately_after_loot():
    """Após loot, se ainda há alvo na battle list, ataca no mesmo tick."""
    env = FakeEnv()
    bot = make_bot(env)
    env.attacking = True
    bot.tick()
    env.attacking = False
    env.has_target = True
    bot.tick()
    idx_loot = env.actions.index(("loot",))
    idx_space = env.actions.index(("space",))
    assert idx_loot < idx_space


def test_tick_walks_to_marker_when_idle():
    env = FakeEnv()
    bot = make_bot(env)
    bot.tick()
    assert env.actions[0] == ("click", 100, 200)


def test_tick_no_walk_when_no_markers():
    env = FakeEnv()
    env.markers = []
    bot = make_bot(env)
    bot.tick()
    assert all(a[0] != "click" for a in env.actions)


def test_does_not_loot_without_prior_attack():
    env = FakeEnv()
    bot = make_bot(env)
    bot.tick()
    assert ("loot",) not in env.actions
