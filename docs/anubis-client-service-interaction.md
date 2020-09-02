<!---
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
-->
# Anubis Client/Service Interaction

Anubis is meant to be a black box, with two ingress/egress locations.
The black box is circumscribed by a VPC that protects its constituent
parts.  The only ingress/egress into the black box is the BFF's
REST-like API and the metrics dashboard.

## Aubis Client <-> BFF

Let's take a closer look into the `anubis-client` and BFF interaction.

The REST-like api is very simple ([see code here](https://github.com/awslabs/benchmark-ai/blob/master/bff/src/bai_bff/http_api.clj#L100-L116))
The system comes with a full client implementation, the [`anubis`](bff/docs/anubis-client.md) client.
The event protocol is JSON - please review the [catalog of defined events](docs/anubis-event-design.md)

## Submitting a benchmark job:

1. Create the event:

``` bash
{
    "message_id" : "$(uuidgen)",
    "client_id"  : "$(get_client_id)",
    "client_version" : "${VERSION}",
    "client_sha1"    : "${MY_SHA1}",
    "client_username" : "$(whoami)",
    "date" : "$(date -u +"%a %b %d %H:%M:%S %Z %Y")",
    "visited"  : [{"svc" : "${SERVICE_NAME}", "tstamp" : $(( $(date +%s) * 1000 )), "version" :"${VERSION}"}],
    "payload"  : {
        "toml" : {
            "descriptor_filename" : "${descriptor_filename##*/}",
            "sha1" : "$(sha1sum ${descriptor_filename} | awk '{print $1}')",
            "doc"  : "$(base64 --wrap=0 ${descriptor_filename})"
        }
    }
}
```


2. POST that event - **/api/job/descriptore**

The resultant call looks like this:

Example

``` bash
curl -s -F submit-event='{
  "message_id": "6CFB79ED-FF98-4200-BAAC-0C12D3DAA711",
  "client_id": "ca2f097889997d8200b9abc2f8d2ec822246845e",
  "client_version": "0.1.0-481dad2",
  "client_sha1": "c541cb4286c1b73c4a3aa5a1fb0a3f3c20424183",
  "client_username": "bellgav",
  "date": "Fri Aug 23 23:26:15 UTC 2019",
  "visited": [
    {
      "svc": "anubis-client",
      "tstamp": 1566602775000,
      "version": "0.1.0-481dad2"
    }
  ],
  "payload": {
    "toml": {
      "descriptor_filename": "example_descriptor.toml",
      "sha1": "fd3e9c0450e55f1cb3cf382a1ae53cb717c1420c",
      "doc": "IyBCZW5jaG1hcmtBSSBtZXRhCnNwZWNfdmVyc2lvbiA9ICIwLjEuMCIKCiMgVGhlc2UgZmllbGRzIGRvbid0IGhhdmUgYW55IGltcGFjdCBvbiB0aGUgam9iIHRvIHJ1biwgdGhleSBjb250YWluCiMgbWVyZWx5IGluZm9ybWF0aXZlIGRhdGEgc28gdGhlIGJlbmNobWFyayBjYW4gYmUgY2F0ZWdvcml6ZWQgd2hlbiBkaXNwbGF5ZWQKIyBpbiB0aGUgZGFzaGJvYXJkLgpbaW5mb10KdGFza19uYW1lID0gIkhlbGxvIHdvcmxkIgpkZXNjcmlwdGlvbiA9ICIiIiBcCiAgICBBIGhlbGxvIHdvcmxkIGV4YW1wbGUgb2YgdXNpbmcgQmVuY2htYXJrIEFJXAogICAgIiIiCgojIDEuIEhhcmR3YXJlCltoYXJkd2FyZV0KaW5zdGFuY2VfdHlwZSA9ICJ0My5zbWFsbCIKc3RyYXRlZ3kgPSAic2luZ2xlX25vZGUiCgojIDIuIEVudmlyb25tZW50CltlbnZdCiMgRG9ja2VyIGh1YiA8aHViLXVzZXI+LzxyZXBvLW5hbWU+Ojx0YWc+IApkb2NrZXJfaW1hZ2UgPSAiZWRpc29uZ3VzdGF2by9iYWktYmVuY2htYXJrcy1oZWxsby13b3JsZDpsYXRlc3QiCgojIDMuIE1hY2hpbmUgbGVhcm5pbmcgcmVsYXRlZCBzZXR0aW5nczogCiMgZGF0YXNldCwgYmVuY2htYXJrIGNvZGUgYW5kIHBhcmFtZXRlcnMgaXQgdGFrZXMKW21sXQpiZW5jaG1hcmtfY29kZSA9ICJweXRob24zIGhlbGxvLXdvcmxkLnB5IgoKIyA0LiBPdXRwdXQKW291dHB1dF0KIyBEZWZpbmUgd2hpY2ggbWV0cmljcyB3aWxsIGJlIHRyYWNrZWQgaW4gdGhpcyBiZW5jaG1hcmsKbWV0cmljcyA9IFsidGhyb3VnaHB1dCIsICJ0aW1lIl0K"
    }
  }
}' http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxx.us-east-1.elb.amazonaws.com:80/api/job/descriptor

```


3. Returns: action-id

Ex: **922ab045-929f-4880-a448-61419583167a**

## Getting Status

GET API: **/api/job/`client-id`/`action-id`**

``` bash
curl -s -X GET -H Content-Type: application/json http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxx.us-east-1.elb.amazonaws.com:80/api/job/ca2f097889997d8200b9abc2f8d2ec822246845e/922ab045-929f-4880-a448-61419583167a?since=0

```


returns:

``` bash
..........
Status: [922ab045-929f-4880-a448-61419583167a]
✊ |e3e89576|Submission has been successfully received...
🐕 |15fd0ea7|fetcher-dispatcher service, node fetcher-dispatcher-545498cb85-kc684: Processing event...
🐕 |2cdac826|Nothing to fetch
🔮 |f30b3b06|sm-executor service, node sm-executor-5cf47c7fc6-pr78q: Processing event...
🔮 |17550710|Unknown engine default
⚡ |37c61759|executor service, node executor-8494f7587d-5mp2m: Processing event...
⚡ |956da08d|Benchmark successfully submitted with job id b-922ab045-929f-4880-a448-61419583167a
⚡ |d106a3c8|executor service, node executor-8494f7587d-5mp2m: Processing event...
👀 |5d3dec05|watcher service, node watcher-5c794647f6-rddhr: Processing event...
👀 |957874e1|Job is pending nodes to scale
👀 |71d6c699|Job is pending nodes to scale
👀 |307173bd|Job is pending nodes to scale
👀 |f150816d|Job is pending nodes to scale
👀 |9297332b|Job is pending nodes to scale
👀 |4bbe7b1a|Job is pending initialization
👀 |def4eb64|Job is pending initialization
👀 |fc97a559|Job is pending initialization
👀 |8f573e10|Job is pending initialization
👀 |889e3d82|Job is pending initialization
👀 |c84b119c|Job is running
👀 |350b0e1c|Metrics available for job 922ab045-929f-4880-a448-61419583167a at http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxx.us-east-1.elb.amazonaws.com/d/IpQu-SNWk/?orgId=1&from=1566602928410&to=1566606528410&var-datasource=Prometheus&var-cluster=&var-namespace=default&var-client_id=ca2f097889997d8200b9abc2f8d2ec822246845e&var-action_id=922ab045-929f-4880-a448-61419583167a
👀 |7d07b329|Job finished with success
👀 |b8b9faa3|Metrics available for job 922ab045-929f-4880-a448-61419583167a at http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxx.us-east-1.elb.amazonaws.com/d/IpQu-SNWk/?orgId=1&from=1566602928410&to=1566602933504&var-datasource=Prometheus&var-cluster=&var-namespace=default&var-client_id=ca2f097889997d8200b9abc2f8d2ec822246845e&var-action_id=922ab045-929f-4880-a448-61419583167a
```

## Getting results

GET API: **/api/job/results**

``` bash
curl -s -X GET -H Content-Type: application/json http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxx.us-east-1.elb.amazonaws.com:80/api/job/results/ca2f097889997d8200b9abc2f8d2ec822246845e/922ab045-929f-4880-a448-61419583167a
```

returns: The stdout of the model code.
