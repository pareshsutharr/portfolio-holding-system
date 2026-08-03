# benchmark_fetcher.py

import os
import requests

from config import BENCHMARKS


DOWNLOAD_FOLDER = "benchmark/downloads"



def download_factsheet(
    benchmark_key
):

    benchmark = BENCHMARKS[benchmark_key]


    file_path = benchmark["pdf_file"]


    os.makedirs(
        os.path.dirname(file_path),
        exist_ok=True
    )


    headers = {
        "User-Agent": "Mozilla/5.0"
    }


    print(
        f"Downloading {benchmark['name']} factsheet..."
    )


    response = requests.get(
        benchmark["url"],
        headers=headers,
        timeout=30
    )


    response.raise_for_status()


    with open(
        file_path,
        "wb"
    ) as file:

        file.write(
            response.content
        )


    print("\nSUCCESS")
    print("Saved:")
    print(file_path)


    return file_path



if __name__ == "__main__":

    for benchmark_key in BENCHMARKS:

        download_factsheet(
            benchmark_key
        )
