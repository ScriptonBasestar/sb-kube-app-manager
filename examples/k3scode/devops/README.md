# Devops

helm template - nexus

```bash
helm template nexus-repository-manager build/nexus-repository-manager --values values/nexus-repository-manager.yaml --create-namespace --namespace devops
```

## Nexus3

admin // admin123
/nexus-data/admin.password

# CI

* drone.io 241
  Apache, Blue Oak Model License
  https://github.com/drone
* screwdriver.cd 990
  Copyright 2016 Yahoo Inc
  https://github.com/screwdriver-cd/screwdriver
* concourse-ci.org 7K
  Apache
  https://github.com/concourse/concourse
* spinnaker.io 9k
  MIT, Apache
  https://github.com/spinnaker
* gocd.org 6.9k
  Apache
  https://github.com/gocd
* Jenkins 21.6k
  MIT
  https://github.com/jenkinsci/jenkins



## Gitlab Runner
https://docs.gitlab.com/runner/install/kubernetes.html
export KUBECONFIG=~/.kube/polypia-cluster
gitlab-runner
kubectl create secret generic s3access \
--namespace devops \
   --from-literal=accesskey="VGFmdQ8LjZblujDRMC1K" \
   --from-literal=secretkey="gvHjCUATUl0NBMPwGAGAjh5AagvNPBsxWbmJsfzu"
