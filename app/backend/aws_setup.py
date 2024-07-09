import logging

import boto3
from boto3.s3.transfer import TransferConfig
from django.conf import settings
from django.contrib.sites.models import Site

config = TransferConfig(
    multipart_threshold=1024 * 10,
    max_concurrency=10,
    multipart_chunksize=1024 * 10,
    use_threads=True,
)

log = logging.getLogger(__name__)


def get_bucket_name():
    return settings.AWS_STORAGE_BUCKET_NAME


def get_expiration_ts():
    return settings.AWS_URL_EXPIRATION


def initialize_upload_storage_server():
    if settings.AWS_S3_REGION_NAME:
        return boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
    return boto3.client("s3")


def initialize_download_storage_server():
    if settings.AWS_S3_REGION_NAME:
        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            config=boto3.session.Config(signature_version="s3v4"),
        )
    else:
        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            config=boto3.session.Config(signature_version="s3v4"),
        )


def download_file(
    server, bucket_name, destination_path, expiration, allow_download=False
):
    try:
        filename = destination_path.split("/")[-1]
        params = {"Bucket": bucket_name, "Key": destination_path}
        if allow_download:
            params = {
                **params,
                **{
                    "ResponseContentDisposition": f'attachment; filename="{filename}"'
                },
            }
        url = server.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expiration
        )
        return True, url
    except Exception as e:
        return False, str(e)


def download(destination_path, allow_download=False):
    if settings.DEBUG is False and settings.TEST is False:
        try:
            bucket_name = get_bucket_name()
            if bucket_name is None:
                log.warning("Empty bucket name")
                return ""
            storage_server = initialize_download_storage_server()
            expiration = get_expiration_ts()
            download_status, download_resp = download_file(
                storage_server,
                bucket_name,
                destination_path,
                expiration,
                allow_download,
            )
            if not download_status:
                log.warning(
                    "Download status: %s. Response: %s. Destination path: %s",
                    download_status,
                    download_resp,
                    destination_path,
                )
                return ""
            return download_resp
        except Exception as e:
            log.exception(e)
            return ""
    else:
        domain_name = Site.objects.first()
        return f"http://{domain_name}/media/{destination_path}"


def extract_text(response, extract_by="LINE"):
    line_text = []
    if response.get("Blocks"):
        for block in response["Blocks"]:
            if block["BlockType"] == extract_by:
                line_text.append(block["Text"])
    return line_text


def print_labels_and_values(field):
    # Only if labels are detected and returned
    if "LabelDetection" in field:
        print(
            "Summary Label Detection - Confidence: {}".format(
                str(field.get("LabelDetection")["Confidence"])
            )
            + ", "
            + "Summary Values: {}".format(
                str(field.get("LabelDetection")["Text"])
            )
        )
        print(field.get("LabelDetection")["Geometry"])
    else:
        print("Label Detection - No labels returned.")
    if "ValueDetection" in field:
        print(
            "Summary Value Detection - Confidence: {}".format(
                str(field.get("ValueDetection")["Confidence"])
            )
            + ", "
            + "Summary Values: {}".format(
                str(field.get("ValueDetection")["Text"])
            )
        )
        print(field.get("ValueDetection")["Geometry"])
    else:
        print("Value Detection - No values returned")


def get_lineitem(expense_fields):
    result = {}
    for f in expense_fields:
        value = None
        label = None
        if "Type" in f:
            label = f["Type"]["Text"]
        if label is None and "LabelDetection" in f:
            label = str(f.get("LabelDetection")["Text"])
        label = "NOLABEL" if label is None else label
        if "ValueDetection" in f:
            value = str(f.get("ValueDetection")["Text"])
        if label != "EXPENSE_ROW":
            result[label] = value
    return result


def get_summary_field(field):
    # Only if labels are detected and returned
    label = None
    value = None
    if "Type" in field:
        if "Text" in field["Type"]:
            label = field["Type"]["Text"]

    if label is None and "LabelDetection" in field:
        label = str(field.get("LabelDetection")["Text"])

    if "ValueDetection" in field:
        value = str(field.get("ValueDetection")["Text"])

    return {"label": label, "value": value}


def ocr_raw_response(s3_obj_key):
    # integrate s3

    # integrate textract
    textract = boto3.client(
        "textract",
        aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    if settings.DEBUG is False and settings.TEST is False:
        textract_document = {
            "S3Object": {
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Name": s3_obj_key,
            }
        }
    else:
        with (settings.BASE_DIR / "media" / s3_obj_key).open("rb") as fp:
            file_bytes = fp.read()
        textract_document = {"Bytes": file_bytes}
    # make OCR on s3 object usign textract
    response = textract.analyze_expense(Document=textract_document)
    return response


def ocr(s3_obj_key):
    data = {"line_item_fields": [], "summary_fields": {}}
    try:
        line_item_fields = []
        summary_fields = {}
        response = ocr_raw_response(s3_obj_key)
        for expense_doc in response["ExpenseDocuments"]:
            for line_item_group in expense_doc["LineItemGroups"]:
                for i, line_items in enumerate(line_item_group["LineItems"]):
                    result = get_lineitem(line_items["LineItemExpenseFields"])
                    line_item_fields.append(result)
            for summary_field in expense_doc["SummaryFields"]:
                result = get_summary_field(summary_field)
                if not result["label"] is None and not result["value"] is None:
                    summary_fields[result["label"]] = result["value"]
        data["line_item_fields"] = line_item_fields
        data["summary_fields"] = summary_fields
    except Exception as e:
        log.exception(e)
    return data
