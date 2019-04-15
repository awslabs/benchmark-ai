from fetcher_dispatcher.args import get_args
from fetcher_dispatcher.loop import run_msg_loop


def main(argv=None):
    args = get_args(argv)
    run_msg_loop(args)


if __name__ == '__main__':
    main()
