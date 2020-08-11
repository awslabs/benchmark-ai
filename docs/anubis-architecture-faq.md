# [Anubis](https://github.com/awslabs/benchmark-ai) Architecture FAQ


*[Anubis](https://github.com/awslabs/benchmark-ai) is a benchmarking solution that is built at Amazon but is designed in a peculiar way. My vision for the project is to build a world-class benchmarking solution not just for Amazon but for the entire ML community (the BHAG: Think Big). I want [Anubis](https://github.com/awslabs/benchmark-ai) to be _**the**_ de facto benchmarking tool used by everyone in the industry! In the context of that vision we built the system almost entirely from best of breed open source tools. The [tenets](/docs/anubis-project-tenets.md) of the project lead us to build Anubis for AWS out-of-the-box, but not only for AWS. It is important for a benchmarking tool to “not have anything up its sleeves” to engender trust - this is a strong forcing function to make sure it is open source, well-built and performant. Our users must be and able to stand by the results.  The design must be elegant enough to support evolution and customization.  The engineering must be grounded in sound engineering principles.  The architecture must provide enough transparency to further engender trust and encourage engagement with a simple interface that delights!*
-[Gavin](https://github.com/gavinmbell)

In this document I will answer common questions about Anubis and provide enough context to convincingly support decisions made. (I hope)

## Q&A: (in no particular order)



* **Q: Why services?**
* A: We created an architecture that would scale and be build on a set of technologies and software practices that would allow it to grow organically. Each service has a distinct concern.  We cleave the software based on the cardinality of the number of instances and elasticity inherent for each concern.  The characteristics of the BFF is different from the Fetcher, is different from the Executor - for example.



* **Q: What are these services?**
* A: There is the BFF (back end for the front end), the Fetcher, the Executor (of which there are currently two flavors) and the Watcher.  Events are passed through, in that order, via Kafka.



* **Q: Why events?**
* A: [Events](/docs/anubis-event-design.md) are a great way to represent data, capture and push around state. The services are transformers of these events.  The primary services move data around via the Kafka event bus.  The there are events that are serially pushed through the system from service to service and then there are broadcast events that every service gets.



* **Q: Why are you using Make?**
* A: The Anubis system is build from a series of services that speak to each over over a message bus.  Services are free to be written in more than one language.  Every language has their own build management tools. In order to uniformly support a polyglot environment we use Make as the lowest common denominator build tool that can delegate to tool specific build apparatus.  Make also provides a lingua-franca for build pipelines.  The CI/CD system only needs to trigger make directives.  There are a fixed set of core make directives that addresses the requirements of all build and deployment pipelines.  Make has been around for a long time and is well battle tested for its function.



* **Q: Why BASH?**
* A: Bash is ideal, as a bootstrapping tool, especially when you are constantly shelling out and taking advantage of *NIX tools.  The CLI client is also implemented in BASH for simplicity and quick development cycle iteration.  Bash is standard on every *NIX machine and thus is a great lowest common denominator scripting language



* **Q: Why Clojure?**
* A: Clojure is an effective, flexible and powerful LISP that sits on the JVM.  Clojure is a LISP and as such a purely functional language.  It excels at data structure manipulation and has powerful features and persistent data structures and fully compatible with Java via simple interop syntax.  Clojure also can natively interop with Python, this makes it the ideal language that answers the training and inference concerns for machine learning.  The way it is used currently is as an edge api service between clients and the system - the other (3) services are written in Python.



* **Q: What’s up with all the IDs?**
* A: There are multiple ID hashes in the events and they allow us to properly address / filter and disambiguate different semantic aspects of what we want from the events.
    * client_id - this semantically identifies the caller.  Answers the question of where is the origin of this message.  This value is used throughout the message passing of the events because it is used as a Kafka partitioning key.  What this means for us is that all the actions from a particular user (+hostname) is guaranteed to be sequentially ordered in time.  This allows us to the possibility of creating state machines (actual state machines not the name of the aws service) for users and follow sequential user journeys, etc.
    * message_id - every message gets a unique message_id.  This provides a means for deduplication and message handling and definitive identification
    * action_id - This semantically represents an action done by the user.  So when a job is submitted to the system it has an action_id and that id is passed through out the life of the event.



* **Q: In the events what is the “visited” key for?**
* A: Every system “stamps” their information onto the event’s visited section and continue to pass it along.  This provides traceability for events and activity through the system.  You can look at a message and understand its path through the system.



* **Q: Commands?**
* A: In order to lower the entropy of the interface / api to the system we have command event objects, inspired by UNIX itself.  this makes it easy for anyone to come up with new commands and not have to rebuild interfaces etc.  They only have to wire in the implementation and route the command to the implementing endpoint service.  All the processing and checking of events you get for free. (not streaming yet but easy to implement).



* **Q: Routing of events?**
* A: The basic unit of the service in Anubis is {[service]→[egress topic *(BAI_APP+<service-name>)*]}. With this unit the system can easily evolve to include different services with different functionality (transformations) allowing easy expansion.



* **Q: Why TOML?**
* A: We researched multiple formats and we wanted a format that was rich enough to capture the tree of data we wanted to specify but simple enough to be intuitive and user friendly.  Even more intuitive than yaml, we have TOML - which is used widely in the Go-lang community and resembles Windoze ini format.



* **Q: Does it do periodic jobs runs?**
* A: Yes, In the submitted descriptor file there is a section where you can specify a ‘scheduling’ attribute that ostensibly is a “crontab” entry.  With that set, this descriptor will be internally resubmitted (and the appropriate bookkeeping done) to have jobs run on a periodic basis.



* **Q: Security?**
* A: The entire installation sits inside of a **VPC**.  All the services are run on Kubernetes and not exposed to the public.  The notable exception is the BFF that is also run as a Kubernetes service and as such can have outside traffic routed to it.  The BFF is not entirely exposed as it asserts a plist that allows Amazon internal traffic only.  Access is provided to Grafana and is secured by Grafana’s security mechanism.  Inside the VPC is a bastion that an authorized user can connect to.



* **Q: Terraform?**
* A: Yes, again, we want to keep this project open source and available to the larger computing community.  Cloud formation is very much an Amazon tool and is not portable.  Terraform also has some nice affordances that Cloud Formation does not have - I can enumerate them later.

### Declarative - The Descriptor submission: (benefits of being document based)

To use Anubis it requires only that the user submits a document, [a descriptor document](https://github.com/awslabs/benchmark-ai/tree/master/executor#descriptor-file), to the service api.  This is typically done through the client command line interface tool “[anubis](https://github.com/awslabs/benchmark-ai/blob/master/bai-bff/docs/anubis-client.md)”.  The document that is submitted is the canonical representation of this run.  This file can be versioned (in git for example) and therefore users can keep close controls over the runs.  When a run is completed there is a full “receipt” event that is ultimately recorded that contains the full description of everything that has taken place for this submission including the versions of every service that has been touched through the process.   And then there is the result of course which you can query to get all the STDOUT output from the run. A huge mantra for this project is version all of the things!!! :-)

### Script mode:

The system allows for your to declaratively specify values along the model / framework / hardware dimensions.  You can bake the model code into the container that has the supported framework.  Or you can declare the generic framework (TF,MXNet,PyTorch) container and then at submission time specify the code you want to have run in the *containered* framework.  The latter scenario is ***script mode***, where code is bundled and submitted with the descriptor and run.  The nice part about script mode is that scripts are fully portable and not tied to your machine or filesystem.  You can share your descriptor file with someone else and they can submit your descriptor, and even though they don’t have the code you used in their possession - they can still run the code you originally posted (see [reproducibility]).  The caveat there is that you have to be using the same Anubis service instantiation. (with a little work this can also be relaxed).

### Reproducibility:

We designed the system to have strong reproducibility guarantees that can be taken advantage of to limit superfluous and redundant work (read: cheaper on resources, easier on the planet, thwarts lazy scientists raising the temperature of the Earth).  The main activities are 1) get descriptor 2) fetch and catalog datasets 3) execute model training / running.  We make sure that all services are versioned and that those versions are stamped into every event.  We cache datasets and manage them.  This means that we don’t pull down datasets that we already have (sort of).  This is a great savings on resources.  A nice side effect of having cached datasets is that over time you build up a library of datasets local to your instance!  Low entropy datasets that have the been checksummed won’t ever have to pulled down each time, and you are guaranteeing that the data is the same and it has not been changed out underneath you ;-).

### Architecture Tenets:

* **FAT Events**: Events should be rich enough such that the recipient of the event has full context to do all the work that is necessary.  It is not architecturally sound to pass waif thin events (usually because of mis-intentioned parsimony) that have to to have their ids resolved externally.  This opens the door to data moving underneath you causing race distributed conditions.  It also means that the resolving service is pummeled making a SPOF.  Having “fat” events makes the system more scalable and loosely coupled.  It also guarantees the correctness of state, which obviates having lots of obtuse distributed locking logic.
* **Traceable Events**: You should always know where an event came from and how it got to you.
* **Structural service + egress queue** as the building block unit.  With this set up you can then mix and match and push messages through the system in a LEGO mix and match way.
* **Version all of the things** (even “services”!!!): You should never be in the dark about exactly what was run in your system.  For some strange reason engineers at Amazon feel that calling something a service means that it doesn’t get to have a version.  That’s crap.  Every service should reflect it’s version to the caller.

### [Project Tenets:](/docs/anubis-project-tenets.md) (Think Big)

* **Enabling “Self Service”** - The tools we build and the solutions that we create must empower our customers.  We teach people how to fish... Better yet, we give them the best fishing rod that allows them to fish in the most productive way!
* **“Push Button”** - Solutions with robust results
    Our solutions are made as simple as possible.  We exceed our end-users expectations with the output from our systems. (*invent and simplify)*
* **Complete Delivery** -
    Our solutions are well packaged and complete; including well produced and rich documentation. (Single document origin point, Clear explanations, helpful images, well sectioned prose, etc.)
* **Clear Mental Model (Transparency)** -
    Our solutions are designed to provide the end user with a clear mental model of what is happening in the system such that the client can effectively use and provide feedback for our products.
* **We use tools that are best of breed with significant mind share.** -
    We build our solutions with tools (and libraries) that give the most flexibility and access to the largest possible audience.  It should be Amazon first, but not Amazon **only.**

* * *

## **If I had to do it over again...**

In the executor, I would have not had the transpiling implemented quite that low level, but perhaps would opt for a template engine. This is not a huge deal but could have saved some time.  I would have also had all the services written in [Clojure](https://clojure.org/).  It is simply the best language to give you as much power for as little syntax.
* * *

**Credits (Original Anubis team):**<br>
[Chance Bair](https://github.com/Chancebair)<br>
[Gavin Bell](https://github.com/gavinmbell)<br>
[Anton Chernov](https://github.com/lebeg)<br>
[Jose Contreras](https://github.com/jlcontreras)<br>
[Edison Muenz](https://github.com/edisongustavo)<br>
[Per da Silva](https://github.com/perdasilva)<br>
[Stanislav Tsukrov](https://github.com/stsukrov)<br>
[Marco deAbreu](https://github.com/marcoabreu)<br>
