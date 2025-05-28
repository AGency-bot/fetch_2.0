import os
import json
import time
import logging
from datetime import datetime
import boto3

REQUIRES = ["snapshot_paths", "cycle_id"]
PROVIDES = ["s3_urls"]

logger = logging.getLogger(__name__)
BASE_DELAY = 0.3
MAX_DELAY = 2.0

def upload_to_s3(local_file_path, s3_subfolder):
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION")
    bucket = os.getenv("S3_BUCKET_NAME")

    missing = [k for k, v in {
        "AWS_ACCESS_KEY_ID": aws_key,
        "AWS_SECRET_ACCESS_KEY": aws_secret,
        "AWS_DEFAULT_REGION": region,
        "S3_BUCKET_NAME": bucket
    }.items() if not v]
    if missing:
        raise EnvironmentError(f"Brakuje zmiennych \u015brodowiskowych: {', '.join(missing)}")

    session = boto3.session.Session()
    s3 = session.client(
        "s3",
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=region
    )

    filename = os.path.basename(local_file_path)
    s3_key = f"{s3_subfolder}/{filename}"

    try:
        start = time.time()
        s3.upload_file(local_file_path, bucket, s3_key)
        s3.put_object_acl(Bucket=bucket, Key=s3_key, ACL='public-read')
        elapsed = time.time() - start

        url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        logger.info(f"Plik przes\u0142any do S3: {url}")

        delay = min(BASE_DELAY + (elapsed / 10), MAX_DELAY)
        time.sleep(delay)

        return url
    except Exception as e:
        logger.error(f"B\u0142\u0105d przy uploadzie {local_file_path}: {e}")
        return None

def run(data):
    logger.info("Wysy\u0142am snapshoty do S3...")

    snapshot_paths = data.get("snapshot_paths")
    cycle_id = data.get("cycle_id", "noid")

    if not snapshot_paths or not isinstance(snapshot_paths, dict):
        raise ValueError("Brak poprawnych danych w snapshot_paths!")

    s3_urls = {}

    for name, path in snapshot_paths.items():
        if not path or not os.path.exists(path):
            logger.warning(f"Pomini\u0119to brakuj\u0105cy plik: {path}")
            continue

        logger.info(f"Uploaduj\u0119 {name} → {path}")
        url = upload_to_s3(path, s3_subfolder=name)
        if url:
            s3_urls[name] = url
        else:
            logger.error(f"Upload nie powi\u00f3d\u0142 si\u0119 dla: {name}")

    if not s3_urls:
        raise RuntimeError("Nie uda\u0142o si\u0119 przes\u0142a\u0107 \u017cadnego snapshotu do S3.")

    return {
        "s3_urls": s3_urls
    }
