# Anubis Setup

(**The Service Utility**)

The `anubis-setup` program is the main program that allows you to instantiate, tear down and operationally maintain the Anubis installation.  This is the go-to script for manipulating the service.

The Anubis service installation is directly linked to the user account used to instantiate it. Those credentials are THE credentials needed to manipulate the instance, this is a 1:1 relationship.  You can consider the cluster _named_ by the owner.

## Let's get started


First thing, get the code...

* Clone this git repository
  (for convenience symlink `anubis-setup` in your $PATH somewhere and make sure it is executable)

Second thing: The prerequisites.

* Bash v5+

* Conda 4.7.5+

* A Unix-like machine

(This is an executable script so don't forget to make sure it is _chmod'ed_ it appropriately - it should already be.  We recommend putting this program in your $PATH)

```shell
%> chmod 755 anubis-setup
```

Next setup your environment.  As mentioned, the Anubis client uses [Conda](https://docs.conda.io/en/latest/miniconda.html) to provide a suitable and predictable environment in which to run.  You only have to do the following command once (per new release).

```shell
%> anubis-setup --env-setup
```

At this point Conda will initialize and begin pulling down the necessary tools for the environment.  This may take a few moments as it fetches and installs these packages.


## Now what?

There are a couple things to understand about `anubis-setup`.  The
first thing is that it is split into two functionalities with
different flags accordingly.

At the first (top) level are _--flags_ that help you with maintenance
and operation of the system.  They help you to quickly poke around the
system and keep it in alignment.

The second level, denoted by everything after the _-- | --driver_ flag
pertains to the actual creation and destruction of the instance
itself.

Now, let's look at the help it will illustrate this dichotomy...

Notice the `--` | `--driver` flags.  This is the gateway into the `anubis-driver` subsystem calls.


``` bash
> anubis-setup --help

                      _     _                     _
                     | |   (_)                   | |
     __ _ _ __  _   _| |__  _ ___ ______ ___  ___| |_ _   _ _ __
    /  _ |  _ \| | | |  _ \| / __|______/ __|/ _ \ __| | | |  _ \
   | (_| | | | | |_| | |_) | \__ \      \__ \  __/ |_| |_| | |_) |
    \__,_|_| |_|\__,_|_.__/|_|___/      |___/\___|\__|\__,_| .__/
                                                            | |
                                                            |_|

This is the administrative command-line tool for the Anubis system

 > anubis-setup --list-profiles          : lists your aws profiles configured in /Users/bellgav/.aws/credentials
                --whoami                 : tells you what the current active profile is
                --set-profile | --as <profile name> : changes your profile to the provided value
                --sync-config-to-profile : synchronized the Anubis configuration state to match your current profile
                --show-service-endpoint  : displays the hostname and port of the Anubis (bff) HTTP API endpoint (used to "--register" with anubis client tool)
                --list-configmaps        : shows a listing of the current configuration maps
                --show-configmap <configmap name> : shows the configuration associated with the supplied configuration name (default: outputs-infrastructure)
                --connect-anubis-shell   : get a shell on the anubis installation (basiton host)
                --query-logs             : creates connection to log search index and brings up front end in browser
                --query-metrics          : creates connection to metrics index (and brings up front end in browser interface)
                --query-graphs           : creates connection to dashboard server (and brings up front end browser interface)
                --query-alerts           : creates connection to alert manager (and brings up front end interface)
                --snoop-events <topic name(s)> : streams event log to terminal
                --force                  : to force execution of some commands (can also be set by setting env var FORCE=1)
                --debug                  : provides more output to the user (can also be set by setting env var DEBUG=1)
                -- | --driver            : consumes ALL subsequent args and dispatches them to Anubis "driver" sub command (see help below)
                --help                   : (this output)

------------------------------------------------------------
                ("Driver" subsystem....)
------------------------------------------------------------

 usage: anubis-driver.py [-h] [--clean] [--destroy] --region REGION
                        --prefix-list-id PREFIX_LIST_ID
                        [--extra-users EXTRA_USERS]
                        [--extra-roles EXTRA_ROLES]
                        [--chime-hook-url CHIME_HOOK_URL]
                        [--run-integration-tests RUN_INTEGRATION_TESTS]
                        [--github-organization GITHUB_ORGANIZATION]
                        [--bucket BUCKET] [--github-branch GITHUB_BRANCH]

optional arguments:
  -h, --help            show this help message and exit
  --clean               Removes current state and configured values
  --destroy             Destroys Anubis infrastructure and pipeline
  --extra-users EXTRA_USERS
                        In order for a user to directly run kubectl commands
                        against the Anubis EKS cluster you must provide that
                        user's IAM ARN
  --extra-roles EXTRA_ROLES
                        Same as extra-users except with AWS IAM roles
  --chime-hook-url CHIME_HOOK_URL
                        Provide a chime URL for notification of pipeline
                        failures
  --run-integration-tests RUN_INTEGRATION_TESTS
  --github-organization GITHUB_ORGANIZATION
  --bucket BUCKET
  --github-branch GITHUB_BRANCH

required arguments:
  --region REGION       AWS region that Anubis infrastructure and services
                        will be instantiated in. There can only be one
                        instantiation of Anubis per account due to IAM role
                        name collisions, etc.
  --prefix-list-id PREFIX_LIST_ID
                        In order to access Anubis infrastructure from corp we
                        can add the corresponding corp prefix list from the
                        Amazon Prefix List Lookup tool
```

## Typical Use Scenarios

### Spreading the news

Once you have successfully instantiated Anubis, you will want to share with your colleagues, users, customers, etc the endpoint that they need to register with their [`anubis` client](bff/docs/anubis-client.md) with "`anubis --register <endpoint>`".

``` bash
> anubis-setup --show-service-endpoint
Fetching service endpoint value...

Configured service endpoint is: [xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxx.us-west-2.elb.amazonaws.com:80]
```

### Keeping things in sync

There is a loose but strongly enforced relationship between the
current user profile (credentials) and the installation state (held in
terraform).  There is a strong need to know who you are and that it is
aligned with the installation.  It is for these reasons we have the flags:

`--list profiles` will let you know what profiles are available for you to assume.
`--whoami` Let's you know what AWS "profile" is currently **persisted** in Anubis.
`--set-profile` or `--as` will let you set who you want to be.  It must be a valid profile, one of those from the listing.
As mentioned before the system will only work if the profile is the same as the profile that performed the installation.  Use `--sync-config-to-profile` to check and make sure that these align.

If things are not congruous between profile and installation state. Do the following to align.
(notice here I am already aligned, so using the **--force** flag to make it actively sync profile and install)

``` bash
> anubis-setup --force --sync-config-to-profile
Current profile: bellgav-dev
YES, current profile and configuration are aligned...

already sync'ed!
Checking for terraform data...
renamed '/Users/bellgav/projects/benchmark-ai/baictl/drivers/aws/cluster/.terraform' -> '/Users/bellgav/projects/benchmark-ai/baictl/drivers/aws/cluster/.terraform.bak'
Synchronizing terraform data: ./baictl sync infra --aws-region=us-west-2 --mode=pull
download: s3://bai-terraform-state-us-west-2-085721722995/kubeflow-ks-app/ks_app/.gitignore to drivers/aws/cluster/.terraform/bai/kubeflow-ks-app/ks_app/.gitignore
download: s3://bai-terraform-state-us-west-2-085721722995/backend.tfvars to drivers/aws/cluster/.terraform/bai/backend.tfvars
download: s3://bai-terraform-state-us-west-2-085721722995/kubeconfig to drivers/aws/cluster/.terraform/bai/kubeconfig
...
removed '/Users/bellgav/projects/benchmark-ai/baictl/drivers/aws/cluster/.terraform.bak/bai/terraform.plan'
removed '/Users/bellgav/projects/benchmark-ai/baictl/drivers/aws/cluster/.terraform.bak/bai/worker_private.pem'
removed directory '/Users/bellgav/projects/benchmark-ai/baictl/drivers/aws/cluster/.terraform.bak/bai'
removed directory '/Users/bellgav/projects/benchmark-ai/baictl/drivers/aws/cluster/.terraform.bak'
Housekeeping...

```
Now you should be able have connectivity with the installation.


### Checking the configuration

At times you want to look at the configuration values that have been used in the system.  Kubernetes is the engine of the system and as such where much of the configuration lives in the form of _configmaps_.  To get a list of the configmaps that are present you can use the `--list-configmaps` flag.  To inspect further into the configmap to see the values that comprise it, use the `--show-configmap` along with one of the configmaps listed. (If you don't provide any configmap name, it will default to _outputs-infrastructure_, which is the primary configmap governing how the main portions of the infrastructure are configured).


### Poking around and inspecting components

There are other times when you want to take a more focused look at the inside of the anubis infrastructure.  You want to connect to data streams and inspect events.  Or you want to manually look at metrics or set alerts or search logs.  This is where the remainig flags come in.

`--connect-anubis-shell` (or `--jump-to-bastion`) will put your into the main Anubis host that is **inside** the VPC that surrounds the installation.  From this vantage point you can survey all of the systems inside the VPC without security impediments.  Needless to say never share keys to the system and observe best security practices.

The `--query-logs`, `--query-metrics`, `--query-graphs`, `--query-alerts` (and `--snoop-events`) flags provide tunnels into the various systems: Kibana (ElasticSearch), PromDash, Grafana, AlertManager (and Kafka) respectively.  They do block for the duration of the tunnel they set up.

Ex:

``` bash
> anubis-setup --query-logs
Navigate to https://localhost:9200/_plugin/kibana/app/kibana#/dev_tools/console?_g=() to access the Kibana dashboard
Ctrl+C to cancel the session.
```
Go to the URL to open the Kibana dashboard (if you have a nice terminal you can ctrl click on the link directly)


For querying Prometheus operational and benchmark user-defined metrics...
``` bash
> anubis-setup --query-metrics
Navigate to http://127.0.0.1:9090/graph to access the Prometheus dashboard
Ctrl+C to cancel the session.
Forwarding from 127.0.0.1:9090 -> 9090
Forwarding from [::1]:9090 -> 9090
```

Get an inside bird's eye view of the Anubis constituent systems.

``` bash
> anubis-setup --connect-anubis-shell
Welcome to Ubuntu 18.04.3 LTS (GNU/Linux 4.15.0-1050 x86_64)

  System information as of Wed Oct  2 16:45:30 UTC 2019

  System load:  0.0               Processes:           91
  Usage of /:   24.4% of 7.69GB   Users logged in:     0
  Memory usage: 21%               IP address for eth0: 172.16.223.216
  Swap usage:   0%


*** System restart required ***
Last login: Tue Oct  1 16:39:52 2019 from 219.232.250.178
ubuntu@ip-172-16-223-961:~$
```

# The Driver Subsystem

### Typical lifecycle tasks

#### Installation

``` bash
./anubis-setup -- --region us-east-1 --prefix-list-id pl-xxxxxxxx
```
(note the `--` flag, indicating that what follows is strictly for the anubis-driver subsystem)

Running this command is idempotent and occasionally it is the right thing to do.  Say you mess up the config directories storing the state of this installation.  Or something happens.  The full span of "operations", in the worst case scenario, would be ["turn it off and turn it on again"](https://www.youtube.com/watch?v=nn2FB1P_Mn8) (caveat: as of this writing there is no persistence that survives bouncing the installation).

#### Adding additional access credentials

Typically you may want to grant access to your system by other users.  To do so use the --extra-users flag with the **arn** of the additional user or, by role with the --extra-roles **<arn>**.

``` bash
./anubis-setup -- --region us-east-1 --prefix-list-id pl-xxxxxxxx --extra-users <arn>
```

#### Tear down

``` bash
./anubis-setup -- --region us-east-1 --prefix-list-id pl-xxxxxxxx --destroy
```
(again note the `--` flag, indicating that what follows is strictly for the anubis-driver subsystem)
