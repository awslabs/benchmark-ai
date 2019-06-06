"""
A script to update the section `# Build status` of the main README.md

WARNING: This is a hacky script, just to make life easier
"""
import json
from typing import Dict, List

import subprocess


def get_badge_links_from_terraform() -> Dict[str, str]:
    outputs = subprocess.check_output(["terraform", "output", "-json"])
    d = json.loads(outputs.decode())
    return d["ci-unit-tests-badge-url"]["value"]


def build_table_with_badges(badge_links: Dict[str, str]):
    l = ["", "| Project | badge |", "|:--------|:------|"]
    for project, badge_link in badge_links.items():
        item = f"| {project} | ![{project}]({badge_link}) |"
        l.append(item)
    return l


def find_build_status_section(readme: List[str]):
    # Find line with `# Build status`
    for start_line_number, line in enumerate(readme):
        if line == "# Build status":
            break
    else:
        raise ValueError("Didn't find line `# Build status`")

    # The first line is the `# Build status`, which we don't want to override
    start_line_number += 1
    # Now find the end of this section
    for end_line_number, line in enumerate(readme[start_line_number + 1 :], start_line_number):
        if line.startswith("# "):
            break
    else:
        raise ValueError("Didn't end of block for `# Build status`")
    return start_line_number, end_line_number


def main():
    with open("../README.md", "r") as f:
        readme = f.read().splitlines()
    start_line_number, end_line_number = find_build_status_section(readme)

    badge_links = get_badge_links_from_terraform()
    table = build_table_with_badges(badge_links)
    readme[start_line_number:end_line_number] = table

    with open("../README.md", "w") as f:
        f.write("\n".join(readme))


if __name__ == "__main__":
    main()
