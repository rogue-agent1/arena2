#!/usr/bin/env python3
"""Arena allocator v2 — bump allocator with regions and reset.

One file. Zero deps. Does one thing well.

Ultra-fast allocation (pointer bump), free entire arena at once.
Used in compilers, game frames, request handling. No individual free.
"""
import sys, time

class Arena:
    def __init__(self, capacity=65536):
        self.buf = bytearray(capacity)
        self.capacity = capacity
        self.offset = 0
        self.alloc_count = 0

    def alloc(self, size, align=8):
        # Align offset
        mask = align - 1
        self.offset = (self.offset + mask) & ~mask
        if self.offset + size > self.capacity:
            raise MemoryError(f"Arena full: need {self.offset + size}, have {self.capacity}")
        ptr = self.offset
        self.offset += size
        self.alloc_count += 1
        return ptr

    def reset(self):
        """Free everything at once — O(1)."""
        self.offset = 0
        self.alloc_count = 0

    def write(self, ptr, data):
        self.buf[ptr:ptr+len(data)] = data

    def read(self, ptr, size):
        return bytes(self.buf[ptr:ptr+size])

    def used(self): return self.offset
    def remaining(self): return self.capacity - self.offset
    def utilization(self): return self.offset / self.capacity

class ScopedArena:
    """Arena with save/restore points for nested scopes."""
    def __init__(self, capacity=65536):
        self.arena = Arena(capacity)
        self.save_stack = []

    def alloc(self, size, align=8):
        return self.arena.alloc(size, align)

    def save(self):
        self.save_stack.append(self.arena.offset)

    def restore(self):
        if self.save_stack:
            self.arena.offset = self.save_stack.pop()

    def reset(self):
        self.arena.reset()
        self.save_stack.clear()

class TypedArena:
    """Arena for fixed-size objects with iteration."""
    def __init__(self, obj_size, capacity=1024):
        self.obj_size = obj_size
        self.arena = Arena(obj_size * capacity)
        self.count = 0
        self.capacity = capacity

    def alloc(self):
        ptr = self.arena.alloc(self.obj_size, align=1)
        self.count += 1
        return ptr

    def get(self, index):
        return self.arena.read(index * self.obj_size, self.obj_size)

    def __len__(self): return self.count

    def reset(self):
        self.arena.reset()
        self.count = 0

def main():
    print("=== Arena Allocator ===\n")
    arena = Arena(4096)
    ptrs = []
    for size in [64, 128, 256, 32, 512]:
        ptr = arena.alloc(size)
        arena.write(ptr, bytes([0xAB] * size))
        ptrs.append((ptr, size))
        print(f"  alloc({size:3d}) → offset={ptr:4d}")
    print(f"  Used: {arena.used()}/{arena.capacity} ({arena.utilization():.1%})")
    arena.reset()
    print(f"  After reset: {arena.used()} bytes used\n")

    # Scoped arena
    print("=== Scoped Arena ===")
    sa = ScopedArena(4096)
    sa.alloc(100)
    print(f"  After outer alloc: {sa.arena.used()}")
    sa.save()
    sa.alloc(200)
    sa.alloc(300)
    print(f"  After inner allocs: {sa.arena.used()}")
    sa.restore()
    print(f"  After restore: {sa.arena.used()} (inner allocs freed)\n")

    # Benchmark
    print("=== Benchmark ===")
    a = Arena(10 * 1024 * 1024)  # 10MB
    t0 = time.perf_counter()
    for _ in range(1000000):
        a.alloc(64, align=8)
    dt = time.perf_counter() - t0
    print(f"  1M allocs (64B each): {dt*1000:.1f}ms ({1000000/dt:,.0f} allocs/s)")
    t0 = time.perf_counter()
    a.reset()
    dt = time.perf_counter() - t0
    print(f"  Reset 10MB arena: {dt*1000000:.1f}µs")

if __name__ == "__main__":
    main()
