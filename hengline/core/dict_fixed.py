class FixedSizeDict:
    """固定大小的字典，当达到最大大小时会删除最旧的条目"""

    """性能优化的固定大小字典"""

    def __init__(self, max_size):
        self.max_size = max_size
        self._keys = [None] * max_size
        self._values = [None] * max_size
        self._index_map: dict[str, int] = {}  # key -> index
        self._current_index: int = 0
        self._count: int = 0

    def __setitem__(self, key, value):
        if key in self._index_map:
            # 更新现有键
            index = self._index_map[key]
            self._values[index] = value
        else:
            # 添加新键
            if self._count < self.max_size:
                index = self._count
                self._count += 1
            else:
                # 覆盖最旧的条目
                index = self._current_index
                old_key = self._keys[index]
                if old_key is not None:
                    del self._index_map[old_key]

            self._keys[index] = key
            self._values[index] = value
            self._index_map[key] = index
            self._current_index = (index + 1) % self.max_size

    def __getitem__(self, key):
        index = self._index_map[key]
        return self._values[index]

    def __contains__(self, key):
        return key in self._index_map

    def __len__(self):
        return self._count

    def items(self):
        for i in range(self._count):
            if self._keys[i] is not None:
                yield (self._keys[i], self._values[i])


if __name__ == '__main__':
    # 使用示例
    fd = FixedSizeDict(3)
    fd['a'] = 1
    fd['b'] = 2
    fd['c'] = 3
    print(fd)  # FixedSizeDict({'a': 1, 'b': 2, 'c': 3})

    fd['d'] = 4  # 超出大小，删除最旧的 'a'
    print(fd)  # FixedSizeDict({'b': 2, 'c': 3, 'd': 4})

    fd['b'] = 22  # 更新现有键，不会删除其他键
    print(fd)  # FixedSizeDict({'c': 3, 'd': 4, 'b': 22})
