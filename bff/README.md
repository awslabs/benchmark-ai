# bai-bff

The service interface for BenchmarkAI

The `bai-bff` is the only user-facing, service-side, service through which all interactions with the Benchmark AI platform takes place.  The client tool, `baictl`, interacts with this service and helps you make requests and launch commands.

## Usage

---



### What do I need before I get started?

* `make`  

  ```shell
  GNU Make 3.81
  Copyright (C) 2006  Free Software Foundation, Inc
  ```

  

  The items below are required for running *local*,  *bare-metal* builds...

* `java` 

  ```shell
  openjdk 11.0.2 2019-01-15
  OpenJDK Runtime Environment 18.9 (build 11.0.2+9)
  OpenJDK 64-Bit Server VM 18.9 (build 11.0.2+9, mixed mode)
  ```

* `clojure`

  ```shell
  %> clj
  Clojure 1.10.0
  user=>
  ```

* docker

  ```shell
  Docker version 18.09.2, build 6247962
  ```

* Kubernetes
  * `kubctrl` 
  * Minikube

---

### How do I build and run this project?

To compile the code locally run `make` 
(below is the full set of make targets and what they do)

```bash
%> make
```



To run the service locally (from the locally built code tree), run the following commands.  The first command sets up the necessary environment variable for the service know what port to listen on. The second command executes the "run" target of the Makefile.

```bash
%> export ENDPOINTS_PORT=8080
%> make run
```



To create local jar distributions use the "dist" target. This will result in two jar files being created under the "./target" directory.

```bash
%> make dist
```

```shell
%> ls -lh target/
total 49128
18M  Apr 24 18:06 bai-bff-0.1.0-standalone.jar
6.1M Apr 24 18:05 bai-bff-0.1.0.jar
```



To run the service (via the jar file) issue the following command

```bash
%> java -jar target/bai-bff-0.1.0-standalone.jar
```



#### You may also build and run this project in a container environment that contains all the necessary prerequisites already and doesn't require you to install anything explicitly (beside `make`).

[todo]



---

### How do I test the codebase and service?



---

### How do I run integration tests?



---

### How do I package this service?



---

### How do I publish this packaged service?



---

### How do I deploy this service in Kubernetes?



---

### How do I monitor this service?

