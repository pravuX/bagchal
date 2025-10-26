import pygame
import random


class ParticleEffect:
    """Simple particle effect for visual feedback"""

    def __init__(self, x, y, color, count=10):
        self.particles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(2, 6)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x,
                'vy': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y,
                'life': 30,
                'color': color
            })

    def update(self):
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.3  # Gravity
            p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, screen):
        for p in self.particles:
            alpha = int(255 * (p['life'] / 30))
            size = max(2, int(4 * (p['life'] / 30)))
            pygame.draw.circle(screen, p['color'],
                               (int(p['x']), int(p['y'])), size)
