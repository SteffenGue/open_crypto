#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is essentially taken from 'https://github.com/sdushantha/gitdir'. Full credit to the author and many thanks!
Smaller adjustments are made, in particular regarding the print statements. The functions are refactored into methods.
The functionality itself remains unchanged.
"""
from typing import Tuple

import re
import os
import urllib.request
import pathlib
import signal
import argparse
import json
import sys
from colorama import Fore, Style, init
from pathlib import Path

from _paths import package_path

init()

# this ANSI code lets us erase the current line
ERASE_LINE = "\x1b[2K"

COLOR_NAME_TO_CODE = {"default": "", "red": Fore.RED, "green": Style.BRIGHT + Fore.GREEN}


class GitDownloader:
    """
    Class to download, in this case update, files directly from the Github repository. This is needed to react on
    frequently changing exchange API mappings without the need to create a new PyPI version. The class is called
    in the runner module, in particular with: runner.update_maps().
    """

    @staticmethod
    def print_text(text: str, color: str = "default", in_place: bool = False, **kwargs) -> None:
        """
        print text to console, a wrapper to built-in print

        @param text: text to print
        @param color: can be one of "red" or "green", or "default"
        @param in_place: whether to erase previous line and print in place
        @param kwargs: other keywords passed to built-in print
        """

        if in_place:
            print("\r" + ERASE_LINE, end="")
        print(COLOR_NAME_TO_CODE[color] + text + Style.RESET_ALL, **kwargs)

    @staticmethod
    def create_url(url: str) -> Tuple[str, str]:
        """
        From the given url, produce a URL that is compatible with Github's REST API. Can handle blob or tree paths.
        @param url: The repository url.
        @return api_url, download_dirs
        """

        repo_only_url = re.compile(r"https:\/\/github\.com\/[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}\/[a-zA-Z0-9]+$")
        re_branch = re.compile("/(tree|blob)/(.+?)/")

        # Check if the given url is a url to a GitHub repo. If it is, tell the
        # user to use 'git clone' to download it
        if re.match(repo_only_url,url):
            print_text("✘ The given url is a complete repository. Use 'git clone' to download the repository",
                       "red", in_place=True)
            sys.exit()

        # extract the branch name from the given url (e.g master)
        branch = re_branch.search(url)
        download_dirs = url[branch.end():]
        api_url = (url[:branch.start()].replace("github.com", "api.github.com/repos", 1) +
                  "/contents/" + download_dirs + "?ref=" + branch.group(2))
        return api_url, download_dirs

    @staticmethod
    def download(repo_url: str,  output_dir: str = "./resources/running_exchanges/") -> None:
        """
        Downloads the files and directories

        @param repo_url: The repository-url.
        @param output_dir: The output directory
        """

        # generate the url which returns the JSON data
        api_url, download_dirs = GitDownloader.create_url(repo_url)

        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        response = urllib.request.urlretrieve(api_url)

        with open(response[0], "r") as f:
            data = json.load(f)
            # getting the total number of files so that we
            # can use it for the output information later

            # If the data is a file, download it as one.
            if isinstance(data, dict) and data["type"] == "file":
                # download the file
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve(data["download_url"], os.path.join(dir_out, data["name"]))
                # bring the cursor to the beginning, erase the current line, and dont make a new line
                GitDownloader.print_text("Downloaded: " + Fore.WHITE + "{}".format(data["name"]), "green", in_place=True)

            for file in data:
                file_url = file["download_url"]
                file_name = file["name"]

                if file_url is not None:
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                    urllib.request.install_opener(opener)
                    # download the file
                    urllib.request.urlretrieve(file_url, output_dir + file['name'])

                    # bring the cursor to the beginning, erase the current line, and dont make a new line
                    GitDownloader.print_text("Downloaded: " + Fore.WHITE + "{}".format(file_name),
                                             "green", in_place=False, end="\n", flush=True)

                else:
                    GitDownloader.download(file["html_url"], flatten, output_dir)


    @staticmethod
    def main() -> None:
        if sys.platform != 'win32':
            # disbale CTRL+Z
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)

        url = "https://github.com/SteffenGue/open-crypto/tree/master/open_crypto/resources/running_exchanges"

        resource_path = package_path + "/resources/running_exchanges/"

        GitDownloader.download(url, output_dir= resource_path)
        GitDownloader.print_text("✔ Exchange mapping update complete", "green", in_place=True)



