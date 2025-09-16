from collections import OrderedDict


class LRUCache:
    """最近最少使用缓存"""

    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return -1
        # 移动到最新位置
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            # 更新现有键的值并移动到最新位置
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                # 删除最旧的条目
                self.cache.popitem(last=False)
            self.cache[key] = value

    def __repr__(self):
        return f"LRUCache({dict(self.cache)})"


if __name__ == '__main__':
    # 使用示例
    cache = LRUCache(2)
    cache.put(1, 'a')
    cache.put(2, 'b')
    print(cache.get(1))  # 'a'
    print(cache)  # LRUCache({2: 'b', 1: 'a'})

    cache.put(3, 'c')  # 超出容量，删除最不常用的键2
    print(cache)  # LRUCache({1: 'a', 3: 'c'})
