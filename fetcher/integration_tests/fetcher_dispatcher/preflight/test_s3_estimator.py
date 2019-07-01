from preflight.data_set_size import DataSetSizeInfo
from preflight.s3_estimator import s3_estimate_size

S3_SINGLE_FILE = "s3://user-bucket/single-file"

S3_FOLDER = "s3://user-bucket/folder"

FILE_SIZE = 4
FILE_COUNT = 2


def test_s3_with_a_file(s3_with_a_file):
    assert DataSetSizeInfo(FILE_SIZE, 1, FILE_SIZE) == s3_estimate_size(S3_SINGLE_FILE, s3_with_a_file)


def test_s3_with_a_folder(s3_with_a_folder):
    assert DataSetSizeInfo(FILE_SIZE * FILE_COUNT, FILE_COUNT, FILE_SIZE) == s3_estimate_size(
        S3_FOLDER, s3_with_a_folder
    )
