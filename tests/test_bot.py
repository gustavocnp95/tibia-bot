from bot import Bot


class FakeEnv:
    def __init__(self):
        self.attacking = False
        self.has_target = False
        self.actions = []
        self.sleeps = []
        self.markers = [{"x": 100, "y": 200}, {"x": 300, "y": 400}]
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
        get_markers=lambda: env.markers,
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
    assert env.actions == []  # nenhuma ação nova
    assert bot.was_attacking is True


def test_tick_loots_after_kill():
    env = FakeEnv()
    bot = make_bot(env)
    # primeiro tick: atacando
    env.attacking = True
    bot.tick()
    # segundo tick: inimigo morreu (attacking=False, has_target=False)
    env.attacking = False
    env.has_target = False
    bot.tick()
    assert ("loot",) in env.actions
    assert bot.was_attacking is False


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
    # sem alvo e sem markers → nenhuma ação de click
    assert all(a[0] != "click" for a in env.actions)


def test_does_not_loot_without_prior_attack():
    env = FakeEnv()
    bot = make_bot(env)
    # nunca esteve em attacking
    bot.tick()
    assert ("loot",) not in env.actions
