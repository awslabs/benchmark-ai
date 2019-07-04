The hello is intended to be used as a "hello world"-test for MPI-jobs
```yaml
apiVersion: kubeflow.org/v1alpha1
kind: MPIJob
metadata:
  name: mpi
spec:
  replicas: 2
  slotsPerWorker: 1
  processingResourceType: cpu
  template:
    metadata:
      creationTimestamp: null
    spec:
      containers:
      - image: mpitest
        imagePullPolicy: Never
        name: mpi
        resources: {}
        command:
          - mpirun
          - --allow-run-as-root
          - echo
          - hello world
```
Expected behavior:
Launcher should contain hello world twice in the log. 

```bash
kubectl logs mpi-launcher-57jnh
+ + POD_NAME=mpi-worker-1POD_NAME=mpi-worker-0

+ shift
+ shift
+ /opt/kube/kubectl exec+  mpi-worker-1/opt/kube/kubectl -- exec /bin/sh mpi-worker-0 -c -- '( test ! -r ./.profile || . ./.profile;  orted -mca ess "env" -mca ess_base_jobid "3386114048" -mca ess_base_vpid 2 -mca ess_base_num_procs "3" -mca orte_node_regex "mpi-launcher-[2:57]jnh,mpi-worker-[1:0-1]@0(3)" -mca orte_hnp_uri "3386114048.0;tcp://10.1.8.16:56451" -mca plm "rsh" -mca plm_rsh_agent "/etc/mpi/kubexec.sh" -mca orte_default_hostfile "/etc/mpi/hostfile" -mca pmix "^s1,s2,cray,isolated" )' /bin/sh
 -c '( test ! -r ./.profile || . ./.profile;  orted -mca ess "env" -mca ess_base_jobid "3386114048" -mca ess_base_vpid 1 -mca ess_base_num_procs "3" -mca orte_node_regex "mpi-launcher-[2:57]jnh,mpi-worker-[1:0-1]@0(3)" -mca orte_hnp_uri "3386114048.0;tcp://10.1.8.16:56451" -mca plm "rsh" -mca plm_rsh_agent "/etc/mpi/kubexec.sh" -mca orte_default_hostfile "/etc/mpi/hostfile" -mca pmix "^s1,s2,cray,isolated" )'
hello world
hello world
```