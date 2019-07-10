# Anubis 

(**The Client**)

The Anubis client allows you to interact with Anubis system to submit Anubis benchmark descriptor files, watch progress and fetch results.  The surface area of this client is small to keep things simple and easy.



The client speaks over HTTP to the Anubis "service_endpoint".  The Anubis tool itself has a RESTful-ish API that the client adheres to.

First thing, download the Anubis client from here.

Second thing: The prerequisites.  

* Bash v5+

* Conda 4.7.5+

* A Unix-like machine

  (This is an executable script so don't forget to chmod it appropriately.  We recommend putting this programin your $PATH)



```shell
%> chmod 755 anubis
```



Next setup your environment.  And mentioned, the Anubis client uses [Conda](https://docs.conda.io/en/latest/miniconda.html) to provide a suitable and predictable environement in which to run.  You only have to do the following command once (per new release).

```shell
%> anubis --env-setup
```

At this point Conda will initialize and begin pulling down the necessary tools for the enviroment.  This may take a few moments as it fetches and installs these packages.



Now let's take a look at the help options.

```shell
%> anubis --help


                       _      _
                      | |    (_)
   __ _  _ __   _   _ | |__   _  ___
  / _  ||  _ \ | | | ||  _ \ | |/ __|
 | (_| || | | || |_| || |_) || |\__ \
  \__,_||_| |_| \__,_||_.__/ |_||___/ ♎

(v0.1.0-481dad2)
-------------------------
AWS: Benchmark AI Client
-------------------------

Brought to you by the cool peeps of the  MXNet-Berlin Team
..........

usage:

This is the command-line, client-side interface to the Bechmark AI service...

 > anubis --submit <descriptor file | action id> [ --script <path to script>] : Returns an "action id" if submission successful
          --status   <action id>   : displays a report of the current status
          --results  <action id>   : displays results report of completed jobs
          --inspect  <message id> [<action-id>] : displays full details of specified message object
          --show-descriptor [<action-id>]       : shows the descriptor acknowledged by Anubis
          --last-action-id         : displays the last action id from a valid submission
          --cancel   <action id>   : cancels the current in progress submission
          --check-version          : checks to see if the version you are running is the latest posted
          --upgrade                : fetches latest version of this tool [anubis]
          --sync-version           : synchronized this tool with that of the service endpoint
          --sync-data              : clean local cached data and refetch from service
          --history                : lists recently returned <action id> : <descriptor path> : <date>
          --register <hostname|IP and PORT of bai service> | Ex: bai.aws.amazon.com:7100
          --unregister             : clears service endpoint from configuration
          --show-registered-service-endpoint : The hostname|IP:PORT of bai service you are using
          --legend                 : displays quick legend of the emojis used
          --help                   : (this output)

          (please use gnu tools for best results!!!)

```



You will need to "register" the service endpoint that the client will communicate with.  This endpoint will be provided to you out-of-band by the adminstrator of the Anubis service installation. For example...

```shell
%> anubis --register anubis-service.amazonaws.com:80
```

Check that it was recorded properly by issuing the command...

```shell
%> anubis --show-registered-service-endpoint
```

And check that the service is actually there with a quick ping...

```shell
%> anubis --ping
```



#### Let's submit our first benchmark!



Once you have described your run via a TOML descriptor file, you may then submit the descriptor and monitor the progress of the run via the Anubis client.  There are example benchmarks available that you may use to get your feet wet.



To submit a benchmark

```shell
%> anbis --submit etc/examples/example_descriptor.toml
```



To see the progress of the benchmark as it passes through the different processing steps in the system.

```shell
%> anubis --status
```

You may use the "watch" flag to watch the progress in real time, as it is reported by the system.

```shell
%> anubis --watch --status
```



Ultimately the benchmark has completed and you will, moments later, have the output of the benchmark made available to you.  You may fetch them by issuing the following...

```shell
$> anubis --results
```



Lets address some terminolgy and some default behavior.

**Action ID**:  This is a UUID value that uniquely represents your run.  This is returned to the terminal after a successfully accepted submission.  It is used as a universal reference to this run. Most commands will assume the latest action id, however, it can always be explicitly set when necessary.

**Status**: Calling the status flag is important because Anubis client obeys a pull model for how it gets data from the Anubis service.  Specifically, it is through status that the local database regarding the run is updated.  Subsequent to fetching status there are other commands you can issue that will take advanage of the local datastore provide further information to you.

```shell
%> anubis --status 6ee29287-ce83-42e4-a618-0e7ac7e7f4af

                       _      _
                      | |    (_)
   __ _  _ __   _   _ | |__   _  ___
  / _  ||  _ \ | | | ||  _ \ | |/ __|
 | (_| || | | || |_| || |_) || |\__ \
  \__,_||_| |_| \__,_||_.__/ |_||___/ ♎

(v0.1.0-481dad2)
-------------------------
AWS: Benchmark AI Client
-------------------------

Brought to you by the cool peeps of the  MXNet-Berlin Team
..........
Status: [6ee29287-ce83-42e4-a618-0e7ac7e7f4af]
✊ |3e4b5571|Submission has been successfully received...
🐕 |3e46b44b|fetcher-dispatcher service, node fetcher-dispatcher-65bdd69fb5-v2rvt: Processing event...
🐕 |bf6875cd|Start fetching datasets
🐕 |a22acbea|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/val-480px-q95.rec', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/ef077b54d8fbecd11e5415c4d8197815/imagenet/480px-q95/val-480px-q95.rec', status=None, type=None, message=None) sent to fetch
🐕 |fc5ed5bd|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/train-480px-q95.rec', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/2859c45c83bb95750a166ac9debc3a6f/imagenet/480px-q95/train-480px-q95.rec', status=None, type=None, message=None) sent to fetch
🐕 |974f620f|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/train-480px-q95.idx', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/3ec8a3510c72bb074b08018db395c561/imagenet/480px-q95/train-480px-q95.idx', status=None, type=None, message=None) sent to fetch
🐕 |8cb89437|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/val-480px-q95.idx', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/da6672ff60a45f4c6f1f2a3d5b11fa16/imagenet/480px-q95/val-480px-q95.idx', status=None, type=None, message=None) sent to fetch
🐕 |9fe17015|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/val-480px-q95.idx', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/da6672ff60a45f4c6f1f2a3d5b11fa16/imagenet/480px-q95/val-480px-q95.idx', status=<FetcherStatus.DONE: 'DONE'>, type=<FetchedType.FILE: 'FILE'>, message=None) processed
🐕 |97c10868|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/train-480px-q95.idx', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/3ec8a3510c72bb074b08018db395c561/imagenet/480px-q95/train-480px-q95.idx', status=<FetcherStatus.DONE: 'DONE'>, type=<FetchedType.FILE: 'FILE'>, message=None) processed
🐕 |44446e46|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/val-480px-q95.rec', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/ef077b54d8fbecd11e5415c4d8197815/imagenet/480px-q95/val-480px-q95.rec', status=<FetcherStatus.DONE: 'DONE'>, type=<FetchedType.FILE: 'FILE'>, message=None) processed
🐕 |3eb8c61e|Dataset DataSet(src='s3://aws-ml-platform-datasets/imagenet/480px-q95/train-480px-q95.rec', md5=None, dst='s3://data-pull-0d673092bee56b36/data_sets/2859c45c83bb95750a166ac9debc3a6f/imagenet/480px-q95/train-480px-q95.rec', status=<FetcherStatus.DONE: 'DONE'>, type=<FetchedType.FILE: 'FILE'>, message=None) processed
🐕 |6a9d38fe|All data sets processed
⚡ |88d1a953|executor service, node executor-8495c466b5-nkk5n: Processing event...
⚡ |3a7084c6|Benchmark successfully submitted with job id 6ee29287-ce83-42e4-a618-0e7ac7e7f4af
```





### Core Design Themes:



#### Reproducibility:

Anubis takes a lot of care in providing **reproducibility** as a core feature.  Every run is named by the action id. You can use the "history" flag to display previous runs. You may re-issue runs, which ostensibly produces a new run with the same input as the run with the action id you specified.

history

```shell
 anubis --history

                       _      _
                      | |    (_)
   __ _  _ __   _   _ | |__   _  ___
  / _  ||  _ \ | | | ||  _ \ | |/ __|
 | (_| || | | || |_| || |_) || |\__ \
  \__,_||_| |_| \__,_||_.__/ |_||___/ ♎

(v0.1.0-481dad2)
-------------------------
AWS: Benchmark AI Client
-------------------------

Brought to you by the cool peeps of the  MXNet-Berlin Team
..........
f54a2b49-010a-4feb-ac9f-c4402b8d3f99 : etc/examples/example_descriptor.toml : Tue Jun 18 22:24:51 CEST 2019
d55a1b69-85f1-4780-ac94-7e495ea7ed08 : etc/examples/example_descriptor2.toml : Tue Jun 18 23:05:10 CEST 2019
6394039b-a88f-4e05-8978-4ec241b88bba : etc/examples/example_descriptor3.toml : Tue Jun 18 23:40:54 CEST 2019
6ee29287-ce83-42e4-a618-0e7ac7e7f4af : /Users/bellgav/projects/benchmark-ai/sample-benchmarks/mlperf-img-class-tflow/descriptor.toml : Wed Jun 19 17:39:59 CEST 2019
1acf24f3-2354-40ea-88df-6d26c85d8293 : /Users/bellgav/projects/benchmark-ai/sample-benchmarks/mlperf-img-class-tflow/descriptor.toml : Thu Jun 20 20:27:22 CEST 2019
91d3c0e4-8a70-4581-b5ae-4d9dbdce05fb : /Users/bellgav/.bai/db/ca2f097889997d8200b9abc2f8d2ec822246845e/a4fcae9c-eb91-41da-a4ae-d7e8d010f3a4/descriptor.toml : Fri Jun 21 13:09:10 CEST 2019
012de1ed-f047-4012-9c59-79dc2cd29f50 : /Users/bellgav/projects/benchmark-ai/sample-benchmarks/mlperf-img-class-tflow/descriptor.toml : Fri Jun 21 15:25:25 CEST 2019
eb56f275-c837-47a0-8265-3a01eb045dfe : /Users/bellgav/projects/benchmark-ai/sample-benchmarks/mlperf-img-class-tflow/descriptor.toml : Fri Jun 21 16:10:20 CEST 2019
de1342cf-3ae6-4e8f-9974-b1eaec6d553c : /Users/bellgav/.bai/db/ca2f097889997d8200b9abc2f8d2ec822246845e/eb56f275-c837-47a0-8265-3a01eb045dfe/descriptor.toml : Fri Jun 21 16:13:20 CEST 2019
4d95cd01-4d05-4df8-a51d-0a2ceff35768 : /Users/bellgav/.bai/db/ca2f097889997d8200b9abc2f8d2ec822246845e/de1342cf-3ae6-4e8f-9974-b1eaec6d553c/descriptor.toml : Fri Jun 21 19:03:56 CEST 2019
c31497c2-c647-432b-853a-fccf5004de43 : etc/examples/example_descriptor.toml : Tue Jun 25 13:08:12 CEST 2019
411d6253-89d6-4c32-a7f7-bbe9783bb32f : etc/examples/example_descriptor.toml : Tue Jun 25 13:26:52 CEST 2019
```

You can see that some runs have been issued using a direct TOML descriptor file submission.  Others are taken from previous runs by providing their action ids. (note eb56f275-c837-47a0-8265-3a01eb045dfe was run and then a subsequent run was done using that action id.). All runs are given a separate action id regardless if they are newly submitted from TOML descriptor or previous action id.



#### Simplicity:

At the end of the day Anubis is a measuring tool, like a ruler or scale ;-).  The afforances of the client tool should be limited and simple so that you don't have to "learn" Anubis, you simply run it and get utility from it.  It measures the "goodness" of machine learning algorithms / frameworks / hardware and provides empirical results that can be used within a larger problem solving scope.  Simply; describe, submit, inspect.

All you bring to the table is your container or code.  We leverage the 

The most typical command line would be:

```shell
anubis --status --watch --submit etc/examples/example_descriptor.toml
```

You may also directly send code to a designated container for execution by specifying the code or top level directory, Anubis handles the rest.

```shell
anubis --status --watch --submit etc/examples/example_descriptor.toml --script /my/code
```



#### Utility:

You can view the history of your runs, as shown above.  You can also fetch the specific descriptor file used for that run (as indicated, by passing in the action-id).

```shell
anubis --show-desc 91d3c0e4-8a70-4581-b5ae-4d9dbdce05fb
```

This will output the exact TOML descriptor used for that run, another nod to **reproducibility**. So even if you nuke the original file, you can still get back to it ;-).  It will also echo back the action id (to double check) and sha1sum of the file.

```bash
...
[[data.sources]]
# Data download URI.
src = "s3://aws-ml-platform-datasets/imagenet/480px-q95/val-480px-q95.idx"
# Path where the dataset is stored in the container FS
path = "/imn/"

# ...

# 4. Output
[output]
# Define which metrics will be tracked in this benchmark
metrics = ["accuracy"]
-------------------------
ActionID: [91d3c0e4-8a70-4581-b5ae-4d9dbdce05fb]
sha1sum : f79b3a29da24489804a173d053c7271793836b5d  -
-------------------------
```

You can also write that file out explicitly with:

```bash
%> anubis --write-desc 91d3c0e4-8a70-4581-b5ae-4d9dbdce05fb /Users/bellgav/.bai/db/ca2f097889997d8200b9abc2f8d2ec822246845e/91d3c0e4-8a70-4581-b5ae-4d9dbdce05fb/descriptor.toml
```



Enjoy!

