import argparse


def build_parser():
    parser = argparse.ArgumentParser(description="CLI tool")
    parser.add_argument("--root")
    parser.add_argument("--out")
    return parser


if __name__ == "__main__":
    build_parser().parse_args()
