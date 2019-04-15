def init_logging(logging_level):
    pass


def main(argv=None):
    from fetcher_dispatcher.args import get_args
    from fetcher_dispatcher.loop import run_msg_loop
    import logging

    args = get_args(argv)

    logging.basicConfig(
        level=args.logging_level
    )
    logger = logging.getLogger("fetcher-dispatcher")
    logger.info("Starting Fetcher Service")
    logger.info("args = %s", args)

    run_msg_loop(args)


if __name__ == '__main__':
    main()
