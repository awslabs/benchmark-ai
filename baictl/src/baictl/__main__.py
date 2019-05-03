import os
import sys
import pkg_resources


def main(argv=None):
    import subprocess

    if not argv:
        argv = sys.argv
    argv = list(argv)
    # We reference the whole directory because we want the whole directory to be extracted so that the Bash scripts and
    # Terraform can reference the files inside.
    bash_dir = pkg_resources.resource_filename("baictl", "bash")
    baictl_bash = os.path.join(bash_dir, "baictl")
    argv[0] = baictl_bash
    cwd = os.path.dirname(baictl_bash)
    return subprocess.call(argv, cwd=cwd)


if __name__ == "__main__":
    sys.exit(main())
