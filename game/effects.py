import pygame
import random


class ParticleEffect:
    """Simple particle effect for visual feedback"""

    def __init__(self, x, y, color, count=10, life=30, gravity=0.3):
        self.particles = []
        self.life = life
        self.gravity = gravity
        for _ in range(count):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(2, 6)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x,
                'vy': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y,
                'life': self.life,
                'color': color
            })

    def update(self):
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += self.gravity  # Gravity
            p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, screen):
        # Draw particles onto a temporary SRCALPHA surface so their alpha channel is preserved
        for p in self.particles:
            alpha = int(255 * (p['life'] / self.life))
            size = max(3, int(4 * (p['life'] / self.life)))
            r, g, b = p['color']
            # create a small surface for the particle with per-pixel alpha
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (r, g, b, alpha), (size, size), size)
            screen.blit(surf, (int(p['x']) - size, int(p['y']) - size))
