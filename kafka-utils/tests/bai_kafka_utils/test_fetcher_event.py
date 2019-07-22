from bai_kafka_utils.events import (
    BenchmarkDoc,
    VisitedService,
    FetcherBenchmarkEvent,
    DataSet,
    FetcherPayload,
    FileSystemObject,
)

BIG_FETCHER_JSON = """{
               "date": "Thu May 02 16:15:42 UTC 2019",
               "authenticated": false,
               "payload": {
                   "toml": {
                       "descriptor_filename": "example_descriptor2.toml",
                       "sha1": "be60cb85620fa041c1bfabd9a9b1c8c1d6be1c78",
                       "doc": "IyBCZW5jaG1hcYS90Zi1pbWFnZW5ldC8iCg==",
                       "verified": true,
                       "contents": {
                           "spec_version": "0.1.0",
                           "data": {
                               "sources": [
                                   {
                                       "path": "~/data/tf-imagenet/",
                                       "src": "s3://bucket/imagenet/train"
                                   },
                                   {
                                       "path": "~/data/tf-imagenet/",
                                       "src": "s3://bucket/imagenet/validation"
                                   }
                               ],
                               "id": "imagenet"
                           },
                           "env": {
                               "privileged": false,
                               "extended_shm": true,
                               "docker_image": "user/repo:tag"
                           },
                           "info": {
                               "task_name": "Example benchmark",
                               "scheduling": "single_run",
                               "description": " Full job description."
                           },
                           "hardware": {
                               "distributed": {
                                   "num_instances": 3
                               },
                               "strategy": "horovod",
                               "instance_type": "p3.8xlarge"
                           },
                           "ml": {
                               "args": "--model=resnet50_v2 --batch-size=32",
                               "benchmark_code": "python /root/train.sh"
                           }
                       }
                   },
                   "datasets": [
                       {
                           "path": "~/data/tf-imagenet/",
                           "src": "s3://bucket/imagenet/train"
                       },
                       {
                           "src": "s3://bucket/imagenet/validation"
                       }
                   ],
                   "scripts": [
                        {
                            "dst": "s3://script-exchange/foo.tar"
                        }
                   ]
               },
               "tstamp": 1556814924121,
               "client_username": "bellgav",
               "action_id": "ffea52eb-c24b-4dd0-b32e-61230db34ad5",
               "visited": [
                   {
                       "svc": "baictl-client",
                       "tstamp": "@@TSTAMP@@",
                       "version": "0.1.0-481dad2"
                   },
                   {
                       "svc": "bai-bff",
                       "tstamp": 1556814924121,
                       "version": "0.0.2"
                   }
               ],
               "message_id": "007bd9f8-f564-4edb-bb48-7380ee562ffc",
               "client_sha1": "c05467317b6765535f1ec60f0aee812d39b35dd2",
               "client_id": "97e7eb322342626974fb171fc5793514b0aea789",
               "client_version": "0.1.0-481dad2",
               "type": "BAI_APP_BFF"
           }"""

EXPECTED_FETCHER_CONTENTS = {
    "spec_version": "0.1.0",
    "data": {
        "sources": [
            {"path": "~/data/tf-imagenet/", "src": "s3://bucket/imagenet/train"},
            {"path": "~/data/tf-imagenet/", "src": "s3://bucket/imagenet/validation"},
        ],
        "id": "imagenet",
    },
    "env": {"privileged": False, "extended_shm": True, "docker_image": "user/repo:tag"},
    "info": {"task_name": "Example benchmark", "scheduling": "single_run", "description": " Full job description."},
    "hardware": {"distributed": {"num_instances": 3}, "strategy": "horovod", "instance_type": "p3.8xlarge"},
    "ml": {"args": "--model=resnet50_v2 --batch-size=32", "benchmark_code": "python /root/train.sh"},
}

EXPECTED_FETCHER_DOC = BenchmarkDoc(
    doc="IyBCZW5jaG1hcYS90Zi1pbWFnZW5ldC8iCg==",
    sha1="be60cb85620fa041c1bfabd9a9b1c8c1d6be1c78",
    contents=EXPECTED_FETCHER_CONTENTS,
    verified=True,
    descriptor_filename="example_descriptor2.toml",
)

EXPECTED_FETCHER_VISITED = [
    VisitedService(svc="baictl-client", tstamp="@@TSTAMP@@", version="0.1.0-481dad2"),
    VisitedService(svc="bai-bff", tstamp=1556814924121, version="0.0.2"),
]

EXPECTED_FETCHER_DATASETS = [DataSet("s3://bucket/imagenet/train"), DataSet("s3://bucket/imagenet/validation")]

EXPECTED_FETCHER_SCRIPTS = [FileSystemObject(dst="s3://script-exchange/foo.tar")]

EXPECTED_FETCHER_EVENT = FetcherBenchmarkEvent(
    action_id="ffea52eb-c24b-4dd0-b32e-61230db34ad5",
    message_id="007bd9f8-f564-4edb-bb48-7380ee562ffc",
    client_id="97e7eb322342626974fb171fc5793514b0aea789",
    client_version="0.1.0-481dad2",
    client_username="bellgav",
    authenticated=False,
    tstamp=1556814924121,
    visited=EXPECTED_FETCHER_VISITED,
    type="BAI_APP_BFF",
    payload=FetcherPayload(
        datasets=EXPECTED_FETCHER_DATASETS, scripts=EXPECTED_FETCHER_SCRIPTS, toml=EXPECTED_FETCHER_DOC
    ),
)


def test_big_fetcher_json():
    event = FetcherBenchmarkEvent.from_json(BIG_FETCHER_JSON)
    assert event == EXPECTED_FETCHER_EVENT
