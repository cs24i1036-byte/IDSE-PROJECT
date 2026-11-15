"""INVISIBLE MAZE - A Decision Tree Classification Adventure.   Run with:  python main.py"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="INVISIBLE MAZE")
    ap.add_argument("--level", type=int, choices=range(1, 6), help="jump straight into a level")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--save", help="path of the JSON save file")
    args = ap.parse_args(argv)
    from game.app import Game
    from game.scenes import GameplayScene, MenuScene
    game = Game(save_path=args.save, fullscreen=args.fullscreen)
    first = GameplayScene(game, args.level, fresh=True) if args.level else MenuScene(game)
    game.run(first)


if __name__ == "__main__":
    main()
