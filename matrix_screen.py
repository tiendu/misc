import random
import shutil
import time
import sys

# ANSI helpers
class ANSI:
    GREEN = '\033[32m'
    RESET = '\033[0m'
    HIDE_CURSOR = '\033[?25l'
    SHOW_CURSOR = '\033[?25h'
    CLEAR = '\033[2J'
    MOVE_CURSOR = '\033[H'

# Abstract screen size provider
class TerminalSizeProvider:
    def get_size(self):
        raise NotImplementedError()

class DefaultScreenSize(TerminalSizeProvider):
    def get_size(self):
        size = shutil.get_terminal_size(fallback=(200, 24))
        return size.columns, size.lines - 1  # Leave space for cursor

# Responsible for rendering frames
class MatrixRenderer:
    def __init__(self, width, height, charset):
        self.width = width
        self.height = height
        self.charset = charset

    def render(self, positions):
        output = [ANSI.MOVE_CURSOR]
        for row in range(self.height):
            line = []
            for col in range(self.width):
                if positions[col] == row:
                    char = random.choice(self.charset)
                    line.append(f'{ANSI.GREEN}{char}{ANSI.RESET}')
                else:
                    line.append(' ')
            output.append(''.join(line))
        sys.stdout.write('\n'.join(output) + '\n')
        sys.stdout.flush()

# Controls where drops fall
class DropController:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.positions = [random.randint(0, self.height) for _ in range(self.width)]

    def update(self):
        for i in range(self.width):
            if random.random() > 0.1:
                self.positions[i] = (self.positions[i] + 1) % self.height
            else:
                self.positions[i] = random.randint(0, self.height // 2)
        return self.positions

# Core orchestrator
class MatrixRainApp:
    def __init__(self, screen: TerminalSizeProvider, charset: str):
        self.screen_provider = screen
        self.charset = charset

    def run(self):
        sys.stdout.write(ANSI.HIDE_CURSOR + ANSI.CLEAR + ANSI.MOVE_CURSOR)
        sys.stdout.flush()
        try:
            while True:
                width, height = self.screen_provider.get_size()
                controller = DropController(width, height)
                renderer = MatrixRenderer(width, height, self.charset)
                while True:
                    positions = controller.update()
                    renderer.render(positions)
                    time.sleep(0.05)
        except KeyboardInterrupt:
            sys.stdout.write(ANSI.SHOW_CURSOR + '\n')
            sys.stdout.flush()
            sys.exit(0)

def main():
    charset = (
        ''.join(chr(c) for c in range(0x30A0, 0x30FF)) +     # Katakana
        ''.join(chr(c) for c in range(0xFF66, 0xFF9D)) +     # Halfwidth Katakana
        ''.join(chr(c) for c in range(0x0030, 0x007A))       # Digits + ASCII
    )
    screen = DefaultScreenSize()
    app = MatrixRainApp(screen, charset)
    app.run()

if __name__ == '__main__':
    main()
