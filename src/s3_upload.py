from __future__ import annotations
"""S3 uploader for LK20 processed curriculum PDFs.

This module provides a small CLI for uploading the PDF files found in
``data/processed`` to an AWS S3 bucket. In order for this script to work,
AWS credentials must already be configured in the environment (for example
via ``aws configure`` or the standard ``AWS_ACCESS_KEY_ID`` /
``AWS_SECRET_ACCESS_KEY`` / ``AWS_DEFAULT_REGION`` environment variables).

Usage
-----
Run the module directly to push all processed PDFs to a bucket::

    python -m s3_upload my-bucket-name --prefix curriculum_pdfs/

Arguments
~~~~~~~~~
* ``bucket`` (positional): The name of the S3 bucket to upload to.
* ``--prefix`` (optional): A key prefix under which the files will be
  placed inside the bucket. Defaults to the bucket root.

The function can also be imported and used programmatically with
``upload_directory``.
"""

from pathlib import Path
import argparse
import sys
from typing import List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from dotenv import load_dotenv
load_dotenv()

from src.utilities import PROCESSED_DIR, log_error


def upload_directory(bucket: str, prefix: str = "") -> None:
    """Upload every ``*.pdf`` in :pydataattr:`utilities.PROCESSED_DIR` to *bucket*.

    Parameters
    ----------
    bucket: str
        The target S3 bucket name.
    prefix: str, optional
        A prefix that will be prepended to every key. For example, with
        ``prefix='curriculum_pdfs/'`` the object key for ``English_G1-10.pdf``
        becomes ``curriculum_pdfs/English_G1-10.pdf``. The prefix **should** end
        with a trailing slash if you want the files grouped inside a virtual
        directory.
    """

    s3 = boto3.client("s3")

    pdf_files: List[Path] = list(PROCESSED_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {PROCESSED_DIR} – nothing to upload.")
        return

    success_count = 0

    for pdf in pdf_files:
        key = f"{prefix}{pdf.name}" if prefix else pdf.name
        try:
            s3.upload_file(str(pdf), bucket, key)
            success_count += 1
            print(f"✓ Uploaded {pdf.name} → s3://{bucket}/{key}")
        except (BotoCoreError, ClientError) as exc:
            log_error(f"Failed to upload {pdf}: {exc}")

    print(f"Finished: {success_count}/{len(pdf_files)} files uploaded.")


def _parse_args(argv: List[str]):
    parser = argparse.ArgumentParser(description="Upload processed PDFs to S3")
    parser.add_argument(
        "bucket",
        help="Name of the destination S3 bucket (must already exist).",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional key prefix (e.g. 'curriculum_pdfs/').",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    upload_directory(args.bucket, args.prefix)
