provider "helm" {
    kubernetes {
        config_path = "/path/to/kube_cluster.yaml"
    }
}

data "helm_repository" "incubator" {
    name = "incubator"
    url  = "https://kubernetes-charts-incubator.storage.googleapis.com"
}

data "helm_repository" "stable" {
    name = "stable"
    url  = "https://kubernetes-charts.storage.googleapis.com"
}

resource "helm_release" "prometheus-operator" {
    depends_on             = ["module.eks"]
    name       = "prometheus-operator"
    repository = "${helm_repository.stable.metadata.0.name}"
    chart      = "prometheus-operator"
    values = [
        "${file("prometheus.values.yaml")}"
    ]
}