import pytest


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def rpush(self, key, value):
        self.ops.append(("rpush", key, value))

    def ltrim(self, key, start, end):
        self.ops.append(("ltrim", key, start, end))

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))

    async def execute(self):
        for op in self.ops:
            if op[0] == "rpush":
                self.redis.lists.setdefault(op[1], []).append(op[2])
        self.ops = []


class FakeRedis:
    """Sustituto en memoria de Valkey, suficiente para SET NX y listas."""

    def __init__(self):
        self.store: dict = {}
        self.lists: dict = {}

    async def set(self, name, value, nx=False, ex=None):
        if nx and name in self.store:
            return None
        self.store[name] = value
        return True

    async def lrange(self, key, start, end):
        return self.lists.get(key, [])

    def pipeline(self, transaction=True):
        return FakePipeline(self)


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()

    for module in ("app.services.dedup_service", "app.services.memory_service"):
        monkeypatch.setattr(f"{module}.get_redis", lambda: redis)

    return redis
