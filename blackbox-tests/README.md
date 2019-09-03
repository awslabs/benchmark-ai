This project is meant to contain blackbox tests for BAI

### Can I run black box tests locally?
Yes. Just pass the bff endpoint to pytest either with an arg **--bff-endpoint** or an env variable **BFF_ENDPOINT**

You can get it through anubis.
```shell
anubis --show-registered-service-endpoint
```
An alternative is to request the endpoint through kubectl.
```shell
export BFF_ENDPOINT=http://$(kubectl get service bai-bff -o jsonpath='{.status.loadBalancer.ingress[*].hostname}')
```

After that you can run blackbox tests locally or from your IDE.